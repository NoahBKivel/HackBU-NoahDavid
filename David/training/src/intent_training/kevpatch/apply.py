"""Apply narrowly checked extensions to the pinned upstream trainer."""

import argparse
from pathlib import Path


def patch_training_source(source: str) -> str:
    """Transform the expected trainer source and fail if an upstream anchor differs."""
    replacements = [
        ("from . import full_ft\n", "from . import full_ft\nfrom intent_training.kevpatch import persistence as intent_persistence\nfrom intent_training.kevpatch import trace as intent_trace\n"),
        ("    a = parse_args()\n", "    a = parse_args()\n    if a.device == 'cuda':\n        from intent_training.kevpatch.kernels import install_required_kernels\n        install_required_kernels()\n"),
        ("def microbatch_plan(reqs, a, world, rank, pairs=None, shapes=None):", "def _native_microbatch_plan(reqs, a, world, rank, pairs=None, shapes=None):"),
        ("def balanced_runs(items, n, cost):", "def microbatch_plan(reqs, a, world, rank, pairs=None, shapes=None):\n    from intent_training.kevpatch.grouping import microbatch_plan as grouped_plan\n    return grouped_plan(sys.modules[__name__], reqs, a, world, rank, pairs, shapes)\n\n\ndef balanced_runs(items, n, cost):"),
        ("    if (a.save_every_steps or a.save_every_minutes or a.resume or a.stop_after) and not a.full_ft:\n        ap.error(\"resume points are for full-weight runs (--full_ft 1)\")\n", ""),
        ("    if a.snapshot_every_steps < 0 or ((fractions or a.snapshot_every_steps) and not a.full_ft):\n        ap.error(\"snapshots (--snapshot_fractions, --snapshot_every_steps >= 0) are for full-weight runs (--full_ft 1)\")", "    if a.snapshot_every_steps < 0:\n        ap.error(\"snapshot_every_steps must be nonnegative\")"),
        ("    sched = torch.optim.lr_scheduler.OneCycleLR(opt,", "    if not a.full_ft:\n        a.save_every_steps = a.save_every_steps or math.ceil(steps / 10)\n        a.snapshot_every_steps = a.snapshot_every_steps or a.save_every_steps\n    sched = torch.optim.lr_scheduler.OneCycleLR(opt,"),
        ("    position = full_ft.load_resume(resume_dir, opt, sched, resume_args) if a.resume else None", "    position = (full_ft.load_resume(resume_dir, opt, sched, resume_args) if a.full_ft else intent_persistence.load_resume(resume_dir, opt, sched, resume_args, model)) if a.resume else None"),
        ("    writer = full_ft.ResumeWriter(resume_dir, background=world > 1) if a.full_ft else None", "    writer = full_ft.ResumeWriter(resume_dir, background=world > 1) if a.full_ft else intent_persistence.LoRAResumeWriter(resume_dir, model, tok, meta)"),
        ("    if a.full_ft and (plan_steps := full_ft.snapshot_steps(steps, full_ft.snapshot_fractions(a.snapshot_fractions), a.snapshot_every_steps)):", "    if plan_steps := full_ft.snapshot_steps(steps, full_ft.snapshot_fractions(a.snapshot_fractions), a.snapshot_every_steps):"),
        ("        snapshots = full_ft.SnapshotWriter(snapshot_root(a), plan_steps, background=world > 1)", "        snapshots = full_ft.SnapshotWriter(snapshot_root(a), plan_steps, background=world > 1) if a.full_ft else intent_persistence.LoRASnapshotWriter(snapshot_root(a), plan_steps, model)"),
        ("                run += terms", "                run += terms\n                intent_trace.observe(a.out, step + 1, part, terms, group_records)"),
        ("                sched.step(); opt.zero_grad(); step += 1", "                sched.step(); opt.zero_grad(); step += 1\n                intent_trace.finish(a.out, step)"),
        ("                if a.full_ft and full_ft.save_due(step,", "                if full_ft.save_due(step,"),
    ]
    for before, after in replacements:
        if source.count(before) != 1:
            raise ValueError(f"The expected trainer anchor does not appear exactly once: {before[:90]!r}.")
        source = source.replace(before, after, 1)
    compile(source, "kev/train.py", "exec")
    return source


def main() -> None:
    """Apply the checked trainer transformation to one explicit source file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    original = args.source.read_text(encoding="utf-8")
    patched = patch_training_source(original)
    args.source.write_text(patched, encoding="utf-8")
    print("Trainer persistence and grouped-batching extensions applied.")


if __name__ == "__main__":
    main()
