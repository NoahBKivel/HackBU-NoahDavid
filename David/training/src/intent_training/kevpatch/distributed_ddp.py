"""Train replicated decision adapters with globally normalized optimizer groups."""

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time


def rank_records(records: list[dict], world: int) -> list[list[dict]]:
    """Balance linked units across ranks without changing their optimizer group."""
    from .grouping import linked_units
    shards = [[] for _ in range(world)]
    for unit in sorted(linked_units(records), key=len, reverse=True):
        rank = min(range(world), key=lambda index: (len(shards[index]), index))
        shards[rank].extend(unit)
    return shards


def reduce_gradients(parameters: list, distributed: bool) -> None:
    """Sum one contiguous gradient vector before any clipping or optimizer update."""
    import torch
    import torch.distributed as dist
    vector = torch.cat([(parameter.grad if parameter.grad is not None else torch.zeros_like(parameter)).reshape(-1)
                        for parameter in parameters])
    if distributed:
        dist.all_reduce(vector, op=dist.ReduceOp.SUM)
    position = 0
    for parameter in parameters:
        gradient = vector[position:position + parameter.numel()].view_as(parameter)
        if parameter.grad is None:
            parameter.grad = gradient.clone()
        else:
            parameter.grad.copy_(gradient)
        position += parameter.numel()


def run(args: argparse.Namespace) -> None:
    """Execute the same fixed shard passes on one GPU or torchrun replicas."""
    import torch
    import torch.distributed as dist
    from torch import nn
    from torch.nn.parallel import DistributedDataParallel
    import kev.train as native
    from .batched_measure import _arguments, _optimizer, _seed
    from .grouping import optimizer_groups
    from .kernels import install_required_kernels, kernel_calls, convolution_calls
    from .measure import training_model
    from .persistence import LoRAResumeWriter, save_checkpoint
    from kev.checkpoint import Meta
    started = time.perf_counter()
    distributed = args.mode != 'reference'
    rank = int(os.environ.get('RANK', '0')) if distributed else 0
    world = int(os.environ.get('WORLD_SIZE', '1')) if distributed else 1
    local_rank = int(os.environ.get('LOCAL_RANK', '0')) if distributed else 0
    torch.cuda.set_device(local_rank)
    if distributed:
        dist.init_process_group('nccl')
    _seed(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    configuration = json.loads(Path(args.config).read_text())
    binding = install_required_kernels()
    tokenizer, model = training_model(configuration)
    records = [json.loads(line) for line in Path(args.data).read_text().splitlines() if line.strip()]
    if args.mode != 'train':
        records = records[:args.limit]
    else:
        random.Random(args.seed).shuffle(records)
    if not records:
        raise ValueError('The distributed input is empty.')
    for index, record in enumerate(records):
        record.setdefault('_meta', {}).setdefault('id', record.get('record_id', str(index)))
        record['_meta'].setdefault('source', 'distributed')
    groups = optimizer_groups(records, args.global_batch)
    steps = len(groups) if args.mode == 'train' else args.steps
    schedule = steps if args.mode == 'train' else math.ceil(args.projection_records / args.global_batch)
    optimizer, scheduler = _optimizer(model, schedule)
    parameters = list(model.trainable_parameters())
    native_args = _arguments(args.max_state, args.cap)
    native_args.batch, native_args.accum = args.global_batch, 1
    meta = Meta(base=configuration['base'], base_revision=configuration['base_revision'], lora=16,
                head_dim=256, weights_dtype='fp32', weights='lora')
    output = Path(args.out)
    if not rank:
        output.mkdir(parents=True, exist_ok=True)

    class ForwardAdapter(nn.Module):
        def __init__(self, decision):
            super().__init__()
            self.decision = decision

        def forward(self, encodings, shared_prefix):
            return self.decision.forward_batch(encodings, shared_prefix)

    wrapper = (DistributedDataParallel(ForwardAdapter(model), device_ids=[local_rank],
               broadcast_buffers=False, find_unused_parameters=False) if distributed else None)

    class Facade:
        def forward_batch(self, encodings, shared_prefix):
            return wrapper(encodings, shared_prefix) if wrapper is not None else model.forward_batch(encodings, shared_prefix)

    facade = Facade()
    startup_seconds = time.perf_counter() - started
    trace = []
    save_interval = max(1, math.ceil(steps / 10))
    for step in range(steps):
        group = groups[step % len(groups)]
        partition_world = world if distributed else args.partition_world
        shards = rank_records(group, partition_world)
        shard_indices = [rank] if distributed else range(partition_world)
        if distributed:
            dist.barrier()
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        tick = time.perf_counter()
        total_loss = torch.zeros((), device='cuda')
        tokens = 0
        passes = []
        optimizer.zero_grad(set_to_none=True)
        for shard_index in shard_indices:
            shard = shards[shard_index]
            if not shard:
                continue
            _seed(args.seed + step * partition_world + shard_index)
            counts = native.state_token_counts(tokenizer, shard)
            shapes = native.plan_shapes(model, tokenizer, native_args, shard, 0, set(), counts)
            cost = lambda items: native.pass_tokens([shape for record in items for shape in shapes[id(record)]], True)
            ordered = sorted(shard, key=lambda record: cost([record]), reverse=True)
            if any(cost([record]) > args.cap for record in ordered):
                raise ValueError('A distributed record exceeds the measured pass cap.')
            number = 1
            chunks = native.balanced_runs(ordered, number, cost)
            while max(map(cost, chunks)) > args.cap:
                number += 1
                chunks = native.balanced_runs(ordered, number, cost)
            with wrapper.no_sync() if wrapper is not None else nullcontext():
                for chunk in chunks:
                    variants = native.encode_batch(model, tokenizer, native_args, chunk, 0, set())
                    loss, _ = native.batch_loss(facade, native_args, variants, 'cuda', {}, None,
                                               torch.autocast('cuda', dtype=torch.bfloat16))
                    normalized = loss / len(group)
                    normalized.backward()
                    total_loss += normalized.detach()
                    tokens += sum(variant.tokens for variant in variants)
                    passes.append({'records': len(chunk), 'padded_tokens': cost(chunk)})
        reduce_gradients(parameters, distributed)
        if distributed:
            dist.all_reduce(total_loss, op=dist.ReduceOp.SUM)
        if step == 0 and not rank and args.mode != 'train':
            torch.save(torch.cat([parameter.grad.detach().reshape(-1).cpu() for parameter in parameters]),
                       output / 'first-gradient.pt')
        gradient_norm = float(torch.nn.utils.clip_grad_norm_(parameters, native.MAX_GRAD_NORM,
                                                            error_if_nonfinite=True))
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        elapsed = torch.tensor(time.perf_counter() - tick, device='cuda', dtype=torch.float64)
        token_count = torch.tensor(tokens, device='cuda', dtype=torch.int64)
        peak = torch.tensor(torch.cuda.max_memory_allocated(), device='cuda', dtype=torch.int64)
        if distributed:
            dist.all_reduce(elapsed, op=dist.ReduceOp.MAX)
            dist.all_reduce(token_count, op=dist.ReduceOp.SUM)
            dist.all_reduce(peak, op=dist.ReduceOp.MAX)
        if not rank:
            trace.append({'step': step + 1, 'loss': float(total_loss), 'seconds': float(elapsed),
                          'records': len(group), 'forward_tokens': int(token_count),
                          'peak_device_bytes': int(peak), 'gradient_norm': gradient_norm,
                          'rank_zero_passes': passes})
            (output / 'progress.json').write_text(json.dumps(trace, indent=2))
            print(json.dumps(trace[-1]), flush=True)
        if args.mode == 'train' and ((step + 1) % save_interval == 0 or step + 1 == steps):
            if not rank:
                target = output / 'snapshots' / f'step-{step + 1:07d}'
                save_checkpoint(target / 'checkpoint', model, tokenizer, meta, {'step': step + 1, 'steps': steps})
                LoRAResumeWriter(output / 'resume', model, tokenizer, meta).save(
                    step + 1, optimizer, scheduler, {'epoch': 0, 'optimizer_group': step + 1,
                                                   'world': world, 'args': vars(args)})
                import modal
                modal.Volume.from_name(configuration['modal_volume']).commit()
            dist.barrier()
    if not rank:
        if args.mode == 'train':
            save_checkpoint(output / 'checkpoint', model, tokenizer, meta, {'step': steps, 'steps': steps})
        result = {'status': 'PASS', 'mode': args.mode, 'world': world,
                  'partition_world': world if distributed else args.partition_world,
                  'startup_seconds': startup_seconds, 'steps': trace,
                  'records_per_hour': sum(row['records'] for row in trace) / sum(row['seconds'] for row in trace) * 3600,
                  'kernel_binding': binding, 'kernel_calls': kernel_calls(),
                  'convolution_calls': convolution_calls(), 'global_batch': args.global_batch,
                  'data_sha256': hashlib.sha256(Path(args.data).read_bytes()).hexdigest(),
                  'finished_at': datetime.now(timezone.utc).isoformat()}
        (output / 'result.json').write_text(json.dumps(result, indent=2))
    if distributed:
        dist.barrier()
        dist.destroy_process_group()


def main() -> None:
    """Parse the distributed continuation or same-workload parity invocation."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['reference', 'distributed', 'train'], required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--cap', type=int, required=True)
    parser.add_argument('--steps', type=int, default=3)
    parser.add_argument('--limit', type=int, default=16)
    parser.add_argument('--partition-world', type=int, default=4)
    parser.add_argument('--global-batch', type=int, default=16)
    parser.add_argument('--max-state', type=int, default=8192)
    parser.add_argument('--projection-records', type=int, default=12200)
    parser.add_argument('--seed', type=int, default=1)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
