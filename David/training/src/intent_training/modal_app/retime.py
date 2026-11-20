"""Time full-cap physical packing of an actual prepared record mixture."""

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time

import modal

ROOT = Path(__file__).resolve().parents[3] if modal.is_local() else Path('/opt/intent-training')
CONFIG = json.loads((ROOT / 'environment.json').read_text(encoding='utf-8-sig'))
app = modal.App(CONFIG['modal_app'])
volume = modal.Volume.from_name(CONFIG['modal_volume'])
image = (modal.Image.from_id(os.environ['INTENT_MEASUREMENT_IMAGE_ID'])
         .add_local_dir(ROOT / 'src/intent_training/assemble',
                        '/opt/intent-training/src/intent_training/assemble', copy=True)
         if modal.is_local() else modal.Image.debian_slim())


@app.function(image=image, gpu='B200', cpu=8, memory=98304,
              timeout=1800, startup_timeout=600, volumes={'/training': volume})
def retime(prepared_root: str, pass_tokens: int, submitted_at: str,
           checkpointing: int, preparation_call: str = '') -> dict:
    """Measure actual packed optimizer work and a complete persistent checkpoint."""
    entered = datetime.now(timezone.utc)
    started = time.perf_counter()
    wait_started = time.perf_counter()
    if preparation_call:
        prepared = modal.FunctionCall.from_id(preparation_call).get(timeout=600)
        if prepared['returncode']:
            raise RuntimeError('The preparation function failed before timing.')
    preparation_wait_seconds = time.perf_counter() - wait_started
    started = time.perf_counter()
    import torch
    import random
    from collections import Counter
    from copy import deepcopy
    from kev.checkpoint import Meta
    from intent_training.assemble.siblings import pack_siblings, kev_fit
    from intent_training.kevpatch.batched_measure import _arguments, _optimizer, _seed, _step
    from intent_training.kevpatch.grouping import optimizer_groups
    from intent_training.kevpatch.kernels import install_required_kernels, kernel_calls, convolution_calls
    from intent_training.kevpatch.measure import training_model
    from intent_training.kevpatch.persistence import LoRAResumeWriter, save_checkpoint
    volume.reload()
    directory = Path(prepared_root)
    if not directory.is_relative_to('/training/prepared'):
        raise ValueError('The timing input must be private prepared records.')
    destination = Path('/training/retiming') / entered.strftime('%Y%m%dT%H%M%S%fZ')
    destination.mkdir(parents=True)
    records = []
    for name in ('main.jsonl', 'native.jsonl'):
        path = directory / name
        if path.exists():
            records.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    if not records:
        raise ValueError('The actual prepared mixture is empty.')
    random.Random(1).shuffle(records)
    _seed(1)
    binding = install_required_kernels()
    model_started = time.perf_counter()
    tokenizer, model = training_model(CONFIG)
    if not checkpointing:
        model.lm.gradient_checkpointing_disable()
    model_load_seconds = time.perf_counter() - model_started
    startup_seconds = time.perf_counter() - started
    fitted = []
    provisional = 0
    predicate = kev_fit(tokenizer, max_state=8192)
    for index, source in enumerate(records):
        record = deepcopy(source)
        for question in record['questions'].values():
            question.setdefault('src', record.get('_meta', {}).get('source', 'timing'))
            if 'label' not in question:
                question['label'] = (next(iter(question['criteria'])) if question['type'] == 'choice'
                                     else 0 if question['type'] == 'score' else False)
                provisional += 1
        meta = record.setdefault('_meta', {})
        meta.setdefault('source', record.get('source', 'timing'))
        meta['id'] = record.get('record_id', f'timing-{index}')
        for sibling in pack_siblings(record, fits=predicate):
            sibling['_meta']['id'] = sibling['_meta'].get('record_id', meta['id'])
            fitted.append(sibling)
    serialized = ''.join(json.dumps(record, sort_keys=True, ensure_ascii=False) + '\n' for record in fitted)
    (destination / 'timing-records.jsonl').write_text(serialized, encoding='utf-8')
    groups = optimizer_groups(fitted, 16)
    snapshot = {name: parameter.detach().cpu().clone() for name, parameter in model.named_parameters()
                if parameter.requires_grad}
    args = _arguments(8192, pass_tokens)
    # Physical packing changes while the normalized optimizer group remains sixteen records.
    args.batch, args.accum = 16, 1
    probes = []
    accepted = False
    for candidate in sorted({pass_tokens, pass_tokens * 4 // 5, pass_tokens * 2 // 5, pass_tokens // 5}, reverse=True):
        args.pass_tokens_max = candidate
        optimizer, scheduler = _optimizer(model, math.ceil(12200 / 16))
        torch.cuda.reset_peak_memory_stats()
        try:
            warm = [_step(model, tokenizer, group, args, optimizer, scheduler, 0) for group in groups]
            peak = torch.cuda.max_memory_allocated()
            accepted = peak <= 0.9 * torch.cuda.get_device_properties(0).total_memory
            probes.append({'pass_tokens': candidate, 'peak_device_bytes': peak,
                           'status': 'PASS' if accepted else 'OVER_MEMORY_LIMIT'})
        except torch.cuda.OutOfMemoryError as error:
            probes.append({'pass_tokens': candidate, 'status': 'OOM', 'error': str(error)})
        (destination / 'memory-probes.json').write_text(json.dumps(probes, indent=2))
        volume.commit()
        if accepted:
            pass_tokens = candidate
            break
        model.zero_grad(set_to_none=True)
        del optimizer, scheduler
        import gc
        gc.collect()
        torch.cuda.empty_cache()
        with torch.no_grad():
            for name, parameter in model.named_parameters():
                if name in snapshot:
                    parameter.copy_(snapshot[name])
    if not accepted:
        raise RuntimeError('No tested full-pass mixture cap fits the GPU memory limit.')
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            if name in snapshot:
                parameter.copy_(snapshot[name])
    del optimizer, scheduler
    _seed(1)
    optimizer, scheduler = _optimizer(model, math.ceil(12200 / 16))
    torch.cuda.reset_peak_memory_stats()
    timings = []
    for cycle in range(2):
        timings.extend(_step(model, tokenizer, group, args, optimizer, scheduler, 0) for group in groups)
        (destination / 'timing-progress.json').write_text(json.dumps({'steps': timings, 'cycle': cycle}, indent=2))
        volume.commit()
    seconds = sum(row['seconds'] for row in timings)
    count = sum(row['records'] for row in timings)
    memory = torch.cuda.get_device_properties(0).total_memory
    peak = max(row['peak_device_bytes'] for row in timings)
    if peak > 0.9 * memory:
        raise RuntimeError('The actual full-cap mixture exceeds the GPU memory gate.')
    torch.cuda.synchronize()
    checkpoint_started = time.perf_counter()
    meta = Meta(base=CONFIG['base'], base_revision=CONFIG['base_revision'], lora=16,
                head_dim=256, weights_dtype='fp32', weights='lora')
    save_checkpoint(destination / 'scratch/checkpoint', model, tokenizer, meta)
    LoRAResumeWriter(destination / 'scratch/resume', model, tokenizer, meta).save(
        len(timings), optimizer, scheduler, {'epoch': 0, 'next_microbatch': len(timings)})
    volume.commit()
    checkpoint_seconds = time.perf_counter() - checkpoint_started
    result = {'status': 'PASS', 'path': str(destination), 'input_parents': len(records),
              'timed_records': count, 'timed_optimizer_steps': len(timings),
              'geometry_only_target_rows': provisional, 'training_labels_created': 0,
              'input_source_counts': dict(Counter(record.get('_meta', {}).get('source', record.get('source', 'unknown')) for record in records)),
              'payload_sha256': hashlib.sha256(serialized.encode()).hexdigest(),
              'records_per_hour': count / seconds * 3600,
              'tokens_per_second': sum(row['forward_tokens'] for row in timings) / seconds,
              'timed_seconds': seconds, 'startup_seconds': startup_seconds,
              'model_load_seconds': model_load_seconds, 'checkpoint_seconds': checkpoint_seconds,
              'launch_to_function_seconds': (entered - datetime.fromisoformat(submitted_at)).total_seconds(),
              'preparation_wait_seconds': preparation_wait_seconds,
              'checkpointing': checkpointing, 'memory_probes': probes,
              'pass_tokens_max': pass_tokens, 'logical_batch': 16, 'physical_batch_limit': 16,
              'max_state': 8192, 'b_state': 8191, 'seed': 1,
              'peak_device_bytes': peak, 'gpu_memory_bytes': memory, 'steps': timings,
              'kernel_binding': binding, 'kernel_calls': kernel_calls(),
              'convolution_calls': convolution_calls()}
    (destination / 'result.json').write_text(json.dumps(result, indent=2))
    volume.commit()
    print(json.dumps(result), flush=True)
    return result
