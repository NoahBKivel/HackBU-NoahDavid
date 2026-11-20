"""Persist complete trainable state and loadable LoRA checkpoints."""

from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import random
import time
from typing import Any


def random_state() -> dict[str, Any]:
    """Capture every random generator used by the trainer and array utilities."""
    import torch
    import numpy as np
    numpy_state = np.random.get_state()
    return {"python": random.getstate(), "torch": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else None,
            "numpy": (numpy_state[0], numpy_state[1].tolist(), *numpy_state[2:])}


def restore_random_state(state: dict[str, Any]) -> None:
    """Restore the captured random generators without advancing them."""
    import torch
    import numpy as np
    random.setstate(state["python"])
    torch.set_rng_state(state["torch"])
    if state["cuda"] is not None:
        torch.cuda.set_rng_state_all(state["cuda"])
    numpy_state = state["numpy"]
    np.random.set_state((numpy_state[0], np.asarray(numpy_state[1], dtype=np.uint32), *numpy_state[2:]))


def trainable_state(model: Any) -> dict[str, Any]:
    """Copy the adapter and pointer parameters without copying the frozen backbone."""
    return {name: value.detach().cpu().clone() for name, value in model.named_parameters() if value.requires_grad}


def restore_trainable_state(model: Any, state: dict[str, Any]) -> None:
    """Restore every trainable tensor and reject missing or extraneous entries."""
    import torch
    parameters = {name: value for name, value in model.named_parameters() if value.requires_grad}
    if parameters.keys() != state.keys():
        raise ValueError("The resume point does not contain exactly the trainable parameter set.")
    with torch.no_grad():
        for name, value in parameters.items():
            if value.shape != state[name].shape or value.dtype != state[name].dtype:
                raise ValueError(f"The saved trainable tensor has incompatible shape or dtype: {name}.")
            value.copy_(state[name].to(value.device))


def save_checkpoint(target: Path, model: Any, tokenizer: Any, meta: Any,
                    info: dict[str, Any] | None = None) -> None:
    """Write a checkpoint with the same adapter, head and tokenizer layout as Kev."""
    from kev.checkpoint import write_meta
    target.mkdir(parents=True, exist_ok=True)
    model.lm.save_pretrained(target)
    head = {name: value.detach().cpu().clone() for name, value in model.head.state_dict().items()}
    write_meta(target, replace(meta, head=head, extra={**meta.extra, "snapshot": info or {}}))
    tokenizer.save_pretrained(target)


class LoRAResumeWriter:
    """Write atomic resume points after complete optimizer steps."""

    def __init__(self, directory: Path, model: Any, tokenizer: Any, meta: Any) -> None:
        self.directory = Path(directory)
        self.model, self.tokenizer, self.meta = model, tokenizer, meta
        self.seconds: list[float] = []

    def save(self, step: int, optimizer: Any, scheduler: Any,
             position: dict[str, Any], after: Any = None) -> None:
        """Persist parameters, optimizer, scheduler, generators and next data position."""
        import torch
        started = time.monotonic()
        if after is not None:
            after.wait()
        target = self.directory / f"step-{step:07d}"
        target.mkdir(parents=True, exist_ok=True)
        payload = {"trainable": trainable_state(self.model), "optimizer": optimizer.state_dict(),
                   "scheduler": deepcopy(scheduler.state_dict()), "rng": random_state()}
        torch.save(payload, target / ".state.pt.tmp")
        os.replace(target / ".state.pt.tmp", target / "state.pt")
        marker = {**position, "step": step, "dir": target.name}
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.directory / ".latest.json.tmp"
        temporary.write_text(json.dumps(marker, sort_keys=True), encoding="utf-8")
        os.replace(temporary, self.directory / "latest.json")
        self.seconds.append(time.monotonic() - started)
        _commit_volume()

    def wait(self) -> None:
        """Return after the synchronous write has finished."""


def load_resume(directory: Path, optimizer: Any, scheduler: Any,
                args: dict[str, Any], model: Any) -> dict[str, Any] | None:
    """Restore a compatible LoRA resume point before any training forward pass."""
    import torch
    directory = Path(directory)
    latest = directory / "latest.json"
    if not latest.exists():
        return None
    position = json.loads(latest.read_text(encoding="utf-8"))
    if position["args"] != args or position["world"] != 1:
        raise ValueError("The saved run arguments or world size do not match this continuation.")
    saved = torch.load(directory / position["dir"] / "state.pt", map_location="cpu", weights_only=True)
    restore_trainable_state(model, saved["trainable"])
    optimizer.load_state_dict(saved["optimizer"])
    scheduler.load_state_dict(saved["scheduler"])
    restore_random_state(saved["rng"])
    return position


class LoRASnapshotWriter:
    """Keep immutable loadable adapter snapshots at the requested save steps."""

    def __init__(self, root: Path, steps: list[int], model: Any) -> None:
        self.root, self.steps, self.model = Path(root), set(steps), model
        self.written: list[dict[str, Any]] = []

    def due(self, step: int) -> bool:
        """Return whether a requested step lacks a completed checkpoint."""
        return step in self.steps and not (self._path(step) / "snapshot.json").exists()

    def missed(self, step: int) -> list[int]:
        """List requested saves at or before a restored step that are missing."""
        return sorted(value for value in self.steps if value <= step and self.due(value))

    def save(self, step: int, lm: Any, finish: Any, info: dict[str, Any]) -> None:
        """Write the adapter before the shared head and tokenizer completion callback."""
        target = self._path(step)
        target.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        lm.save_pretrained(target)
        finish(target)
        seconds = time.monotonic() - started
        details = {**info, "write_seconds": seconds}
        (target / "snapshot.json").write_text(json.dumps(details), encoding="utf-8")
        self.written.append(details)
        _commit_volume()

    def wait(self) -> None:
        """Return after all synchronous snapshots have finished."""

    def _path(self, step: int) -> Path:
        return self.root / f"step-{step:07d}" / "checkpoint"


def _commit_volume() -> None:
    if name := os.environ.get("INTENT_TRAINING_VOLUME"):
        import modal
        modal.Volume.from_name(name).commit()


def restore_distributed_continuation(directory: Path, optimizer: Any, scheduler: Any, model: Any, total_steps: int) -> dict[str, Any]:
    """Restore a completed distributed step and verify every restored state value."""
    import hashlib
    import torch
    directory = Path(directory)
    position = json.loads((directory / "latest.json").read_text(encoding="utf-8"))
    step = position.get("next_global_step")
    if (position.get("epoch") != 0 or not isinstance(step, int) or isinstance(step, bool)
            or step != position.get("step") or not 0 < step < total_steps
            or position.get("dir") != f"step-{step:07d}"):
        raise ValueError("Invalid distributed continuation cursor.")
    path = directory / position["dir"] / "state.pt"
    saved = torch.load(path, map_location="cpu", weights_only=True)
    if set(saved) != {"trainable", "optimizer", "scheduler", "rng"}:
        raise ValueError("Incomplete continuation state.")
    restore_trainable_state(model, saved["trainable"])
    optimizer.load_state_dict(saved["optimizer"])
    scheduler.load_state_dict(saved["scheduler"])
    restore_random_state(saved["rng"])

    def equal(a: Any, b: Any) -> bool:
        if isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor):
            return a.dtype == b.dtype and a.shape == b.shape and torch.equal(a.cpu(), b.cpu())
        if isinstance(a, dict) and isinstance(b, dict):
            return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
        return a == b
    actual = {"trainable": trainable_state(model), "optimizer": optimizer.state_dict(),
              "scheduler": scheduler.state_dict(), "rng": random_state()}
    for key in saved:
        if not equal(saved[key], actual[key]):
            raise ValueError(f"Restored continuation state differs: {key}")
    digest = hashlib.sha256()
    for name, tensor in sorted(actual["trainable"].items()):
        digest.update(name.encode()); digest.update(tensor.contiguous().view(torch.uint8).numpy().tobytes())
    return {"step": step, "state_path": str(path), "trainable_sha256": digest.hexdigest(),
            "learning_rates": [group["lr"] for group in optimizer.param_groups],
            "state_verified": True}
