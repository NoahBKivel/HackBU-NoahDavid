"""Compare measured padding and SDPA fixes with the native optimizer path."""

from contextlib import nullcontext
import json
import math
from pathlib import Path
import time
from typing import Any


def attention_check() -> dict[str, Any]:
    """Check outputs and all input gradients against explicit causal-mask SDPA."""
    import torch
    import torch.nn.functional as functional
    from .prefix_attention import prefix_mask, prefix_sdpa
    torch.manual_seed(11)
    checks = []
    for state in (True, False):
        lengths = [7, 3] if state else [7, 7, 3, 3]
        n, width, prefix = len(lengths), (7 if state else 3), 7
        real = (torch.arange(prefix, device='cuda')[None] >=
                prefix - torch.tensor(lengths, device='cuda')[:, None])
        causal = torch.ones(width, width, device='cuda', dtype=torch.bool).tril()
        active = real if state else torch.tensor([[1, 1, 1], [1, 0, 0], [1, 1, 0], [1, 1, 1]],
                                                  device='cuda', dtype=torch.bool)
        allow = (causal[None] & real[:, None, :]) if state else torch.cat(
            [real[:, None, :].expand(-1, width, -1), causal[None] & active[:, None, :]], -1)
        eye = torch.eye(width, device='cuda', dtype=torch.bool)[None]
        if state:
            allow = allow | eye
        else:
            allow[:, :, -width:] |= eye
        source = [torch.randn(n, heads, size, 8, device='cuda') for heads, size in
                  ((4, width), (2, width if state else prefix + width), (2, width if state else prefix + width))]
        weight = torch.randn_like(source[0]) * active[:, None, :, None]
        values = []
        grads = []
        for optimized in (False, True):
            q, k, v = [value.detach().clone().requires_grad_() for value in source]
            if optimized:
                answer, _ = prefix_sdpa(None, q, k, v, prefix_mask(allow, q.dtype, 'sdpa'))
                answer = answer.transpose(1, 2)
            else:
                answer = functional.scaled_dot_product_attention(
                    q, k.repeat_interleave(2, 1), v.repeat_interleave(2, 1), attn_mask=allow[:, None])
            (answer * weight).sum().backward()
            values.append((answer * active[:, None, :, None]).detach())
            grads.append([value.grad.detach() for value in (q, k, v)])
        output_gap = float((values[0] - values[1]).abs().max())
        gradient_gap = max(float((left - right).abs().max()) for left, right in zip(*grads))
        checks.append({'state': state, 'output_max_abs': output_gap,
                       'input_gradient_max_abs': gradient_gap,
                       'status': 'PASS' if output_gap < 2e-5 and gradient_gap < 2e-5 else 'FAIL'})
        with torch.autocast('cuda', dtype=torch.bfloat16):
            mixed, _ = prefix_sdpa(None, source[0], source[1], source[2].to(torch.bfloat16),
                                   prefix_mask(allow, source[0].dtype, 'sdpa'))
        checks.append({'state': state, 'mixed_precision_dtype': str(mixed.dtype),
                       'status': 'PASS' if mixed.dtype == torch.bfloat16 else 'FAIL'})
    return {'status': 'PASS' if all(row['status'] == 'PASS' for row in checks) else 'FAIL', 'checks': checks}


def compare(records_path: str, output: str, config: dict[str, Any], pass_tokens: int,
            projection_records: int, volume: Any, prior_output: str = '',
            native_only: bool = False) -> dict[str, Any]:
    """Measure production grouping, padding-free attention and checkpointing on fixed records."""
    import torch
    from .batched_measure import _arguments, _optimizer, _seed, _step
    from .grouping import optimizer_groups
    from .kernels import install_required_kernels
    from .measure import training_model
    from .prefix_attention import padding_free_attention
    destination = Path(output)
    destination.mkdir(parents=True)

    def save(name: str, data: Any) -> None:
        (destination / f'{name}.json').write_text(json.dumps(data, indent=2))
        volume.commit()
        print(json.dumps({'event': name, 'path': output}), flush=True)

    mini = attention_check() if not native_only else {'status': 'NOT_REQUIRED_FOR_NATIVE_PATH'}
    save('attention-check', mini)
    if not native_only and mini['status'] != 'PASS':
        return {'status': 'ATTENTION_CHECK_FAIL', 'path': output, 'check': mini}
    _seed(1)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    install_required_kernels()
    tokenizer, model = training_model(config)
    records = [json.loads(line) for line in Path(records_path).read_text().splitlines() if line.strip()]
    groups = optimizer_groups(records, 16)
    snapshot = {name: parameter.detach().cpu().clone() for name, parameter in model.named_parameters()
                if parameter.requires_grad}
    memory = torch.cuda.get_device_properties(0).total_memory

    def reset(checkpointing: bool) -> tuple[Any, Any]:
        model.zero_grad(set_to_none=True)
        with torch.no_grad():
            for name, parameter in model.named_parameters():
                if name in snapshot:
                    parameter.copy_(snapshot[name])
        if checkpointing:
            model.lm.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        else:
            model.lm.gradient_checkpointing_disable()
        _seed(1)
        torch.cuda.empty_cache()
        return _optimizer(model, math.ceil(projection_records / 16))

    args = _arguments(8192, pass_tokens)
    args.batch, args.accum = 16, 1
    parity = json.loads((Path(prior_output) / 'parity-progress.json').read_text()) if prior_output and not native_only else []
    if parity and [row['name'] for row in parity] != ['reference', 'repeat']:
        raise ValueError('Only the two immutable reference runs may be reused.')
    names = () if native_only else (('padding_free',) if parity else ('reference', 'repeat', 'padding_free'))
    for name in names:
        context = padding_free_attention if name == 'padding_free' else nullcontext
        with context():
            optimizer, scheduler = reset(True)
            if name == 'padding_free':
                with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,
                                                       torch.profiler.ProfilerActivity.CUDA]) as profiler:
                    _step(model, tokenizer, groups[0], args, optimizer, scheduler, 0)
                kernels = sorted({event.name for event in profiler.events()
                                  if 'CUDA' in str(getattr(event, 'device_type', ''))})
                save('attention-kernels', {'kernels': kernels})
            else:
                _step(model, tokenizer, groups[0], args, optimizer, scheduler, 0)
            del optimizer, scheduler
            optimizer, scheduler = reset(True)
            rows = [_step(model, tokenizer, groups[0], args, optimizer, scheduler, 0) for _ in range(2)]
            parity.append({'name': name, 'steps': rows})
            del optimizer, scheduler
            save('parity-progress', parity)
    gate = {'status': 'NOT_ATTEMPTED', 'runs': []}
    if not native_only:
        reference, repeat, candidate = (row['steps'] for row in parity)
        floor = max(abs(a['loss'] - b['loss']) / max(abs(a['loss']), 1e-12) for a, b in zip(reference, repeat))
        gap = max(abs(a['loss'] - b['loss']) / max(abs(a['loss']), 1e-12) for a, b in zip(reference, candidate))
        gate = {'status': 'PASS' if gap <= max(floor, 1e-3) else 'FAIL',
                'max_relative_loss_difference': gap, 'same_seed_relative_noise_floor': floor,
                'runs': parity}
    save('attention-parity', gate)
    scenarios = [('reference', True, pass_tokens), ('reference', False, pass_tokens // 2),
                 ('reference', False, pass_tokens * 3 // 4)]
    if gate['status'] == 'PASS':
        scenarios += [('padding_free', True, pass_tokens),
                      ('padding_free', False, pass_tokens // 2),
                      ('padding_free', False, pass_tokens * 3 // 4)]
    measurements = []
    for name, checkpointing, cap in scenarios:
        args.pass_tokens_max = cap
        context = padding_free_attention if name == 'padding_free' else nullcontext
        with context():
            optimizer, scheduler = reset(checkpointing)
            torch.cuda.reset_peak_memory_stats()
            try:
                for group in groups:
                    _step(model, tokenizer, group, args, optimizer, scheduler, 0)
                warm_peak = torch.cuda.max_memory_allocated()
                if warm_peak > 0.9 * memory:
                    measurements.append({'name': name, 'checkpointing': checkpointing,
                                         'cap': cap, 'status': 'OVER_MEMORY_LIMIT', 'peak': warm_peak})
                    continue
                del optimizer, scheduler
                optimizer, scheduler = reset(checkpointing)
                torch.cuda.reset_peak_memory_stats()
                rows = []
                for _ in range(2):
                    rows += [_step(model, tokenizer, group, args, optimizer, scheduler, 0) for group in groups]
                seconds = sum(row['seconds'] for row in rows)
                count = sum(row['records'] for row in rows)
                peak = torch.cuda.max_memory_allocated()
                measurements.append({'name': name, 'checkpointing': checkpointing, 'cap': cap,
                                     'status': 'PASS' if peak <= 0.9 * memory else 'OVER_MEMORY_LIMIT',
                                     'steps': rows, 'peak': peak, 'seconds': seconds, 'records': count,
                                     'records_per_hour': count / seconds * 3600,
                                     'useful_tokens_per_second': sum(r['forward_tokens'] for r in rows) / seconds,
                                     'padded_tokens_per_second': sum(r['padded_tokens'] for r in rows) / seconds,
                                     'projected_full_run_hours': projection_records / count * seconds / 3600})
            except torch.cuda.OutOfMemoryError:
                measurements.append({'name': name, 'checkpointing': checkpointing, 'cap': cap, 'status': 'OOM'})
                model.zero_grad(set_to_none=True)
            finally:
                del optimizer, scheduler
                torch.cuda.empty_cache()
            save('measurements', measurements)
    result = {'status': 'MEASURED', 'path': output, 'attention_parity': gate,
              'measurements': measurements, 'gpu_memory_bytes': memory,
              'input_records': len(records), 'geometry_only': True, 'training_labels_created': 0}
    save('result', result)
    return result
