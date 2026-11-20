"""Exercise grouped training and exact continuation state."""

import ast
import copy
import math
from pathlib import Path
import random
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intent_training.kevpatch.apply import patch_training_source
from intent_training.kevpatch.grouping import linked_units, microbatch_plan, optimizer_groups


def native_planner():
    source = ast.parse((ROOT / "vendor" / "kev" / "kev" / "train.py").read_text(encoding="utf-8"))
    nodes = [node for node in source.body if isinstance(node, ast.FunctionDef)
             and node.name in {"pass_tokens", "balanced_runs"}]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "upstream-planner", "exec"), namespace)
    return SimpleNamespace(**namespace)


def records(count):
    return [{"state": "text " * (i + 1), "questions": {"q": {"type": "noul"}},
             "_meta": {"id": str(i)}} for i in range(count)]


def test_pair_and_sibling_links_are_transitive():
    rows = records(5)
    rows[0]["_meta"]["pair_id"] = rows[1]["_meta"]["pair_id"] = "pair"
    rows[1]["_meta"]["sibling_group"] = rows[2]["_meta"]["sibling_group"] = "siblings"
    rows[3]["_meta"]["parent_id"] = "2"
    assert [len(unit) for unit in linked_units(rows)] == [4, 1]


@pytest.mark.parametrize("count", [1, 15, 16, 17, 63, 100])
def test_groups_preserve_every_record_and_exact_step_count(count):
    rows = records(count)
    for i in range(0, count - 1, 2):
        rows[i]["_meta"]["pair_id"] = rows[i + 1]["_meta"]["pair_id"] = str(i)
    random.Random(count).shuffle(rows)
    groups = optimizer_groups(rows, 16)
    assert len(groups) == math.ceil(count / 16)
    assert max(map(len, groups)) <= 16
    assert sorted(id(row) for group in groups for row in group) == sorted(map(id, rows))
    locations = {id(row): i for i, group in enumerate(groups) for row in group}
    for unit in linked_units(rows):
        assert len({locations[id(row)] for row in unit}) == 1


def test_pass_cap_keeps_pair_within_step_and_can_split_its_passes():
    rows = records(20)
    rows[0]["_meta"]["pair_id"] = rows[-1]["_meta"]["pair_id"] = "linked"
    shapes = {id(row): [(100 + i * 5, [20, 30])] for i, row in enumerate(rows)}
    args = SimpleNamespace(batch=2, accum=8, shared_prefix=1, length_sort=1, pass_tokens_max=300)
    native = native_planner()
    plan = microbatch_plan(native, rows, args, 1, 0, shapes=shapes)
    by_step = [[]]
    for chunk, normalizer, ends in plan:
        assert native.pass_tokens([shape for row in chunk for shape in shapes[id(row)]], 1) <= args.pass_tokens_max
        by_step[-1].extend(chunk)
        if ends:
            assert normalizer == len(by_step[-1])
            by_step.append([])
    assert len(by_step) - 1 == math.ceil(len(rows) / 16)
    assert any(rows[0] in group and rows[-1] in group for group in by_step)


def test_impossible_group_step_cardinality_fails():
    rows = records(17)
    for row in rows:
        row["_meta"]["pair_id"] = "all"
    with pytest.raises(ValueError, match="Too few"):
        optimizer_groups(rows, 16)


def test_late_large_unit_does_not_inflate_effective_batch():
    rows = records(40)
    for row in rows[-15:]:
        row["_meta"]["sibling_group"] = "large"
    groups = optimizer_groups(rows, 16)
    assert len(groups) == math.ceil(len(rows) / 16)
    assert max(map(len, groups)) <= 16
    assert any(len(group) >= 15 and all(row in group for row in rows[-15:]) for group in groups)


def test_unit_larger_than_effective_batch_fails_instead_of_changing_recipe():
    rows = records(40)
    for row in rows[:17]:
        row["_meta"]["sibling_group"] = "oversize"
    with pytest.raises(ValueError, match="exceeds"):
        optimizer_groups(rows, 16)


def test_single_record_over_measured_cap_fails():
    rows = records(1)
    args = SimpleNamespace(batch=2, accum=8, shared_prefix=1, length_sort=1, pass_tokens_max=30)
    with pytest.raises(ValueError, match="single record"):
        microbatch_plan(native_planner(), rows, args, 1, 0, shapes={id(rows[0]): [(100, [20])]})


def test_full_cap_packing_preserves_logical_step_normalization():
    rows = records(32)
    shapes = {id(row): [(100, [20])] for row in rows}
    args = SimpleNamespace(batch=2, accum=8, shared_prefix=1, length_sort=1, pass_tokens_max=1000)
    native = native_planner()
    plan = microbatch_plan(native, rows, args, 1, 0, shapes=shapes)
    assert [len(chunk) for chunk, _, _ in plan] == [8, 8, 8, 8]
    assert [normalizer for _, normalizer, _ in plan] == [16] * 4
    assert sum(ending for _, _, ending in plan) == 2
    assert all(native.pass_tokens([shape for row in chunk for shape in shapes[id(row)]], 1) <= 1000
               for chunk, _, _ in plan)


def test_checked_patch_matches_source_and_refuses_changed_anchor():
    source = (ROOT / "vendor" / "kev" / "kev" / "train.py").read_text(encoding="utf-8")
    patched = patch_training_source(source)
    assert "intent_persistence.load_resume" in patched
    assert "intent_persistence.LoRASnapshotWriter" in patched
    assert "intent_trace.finish" in patched
    with pytest.raises(ValueError, match="anchor"):
        patch_training_source(source.replace("from . import full_ft", "from . import changed"))


def test_resume_restores_weights_optimizer_scheduler_and_every_rng(tmp_path):
    torch = pytest.importorskip("torch")
    import numpy as np
    from intent_training.kevpatch.persistence import LoRAResumeWriter, load_resume

    def setup(seed):
        torch.manual_seed(seed)
        random.seed(seed)
        np.random.seed(seed)
        model = torch.nn.Sequential(torch.nn.Linear(3, 7), torch.nn.Dropout(0.3), torch.nn.Linear(7, 2))
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.003)
        scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=0.003, total_steps=12)
        return model, optimizer, scheduler

    def train(model, optimizer, scheduler, start, end):
        losses = []
        for _ in range(start, end):
            inputs = torch.randn(4, 3) + random.random() + np.random.random()
            loss = model(inputs).square().mean()
            loss.backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            losses.append(loss.item())
        return losses

    baseline, base_opt, base_sched = setup(8)
    expected = train(baseline, base_opt, base_sched, 0, 12)
    interrupted, first_opt, first_sched = setup(8)
    before = train(interrupted, first_opt, first_sched, 0, 5)
    writer = LoRAResumeWriter(tmp_path / "resume", interrupted, None, None)
    writer.save(5, first_opt, first_sched, {"args": {"data": "frozen"}, "world": 1, "epoch": 0, "microbatch": 5})
    restored, new_opt, new_sched = setup(999)
    position = load_resume(tmp_path / "resume", new_opt, new_sched, {"data": "frozen"}, restored)
    after = train(restored, new_opt, new_sched, position["microbatch"], 12)
    assert before + after == expected
    assert new_sched.state_dict() == base_sched.state_dict()
    assert all(torch.equal(value, restored.state_dict()[name]) for name, value in baseline.state_dict().items())
    for left, right in zip(base_opt.state.values(), new_opt.state.values()):
        assert left.keys() == right.keys()
        assert all(torch.equal(left[key], right[key]) for key in left)


def test_interpolation_uses_merged_products_and_exact_endpoints():
    torch = pytest.importorskip("torch")
    from intent_training.kevpatch.interpolate import interpolate_state
    base = torch.tensor([[2.0, 4.0], [1.0, 3.0]])
    a0, b0 = torch.tensor([[1.0, 0.0]]), torch.tensor([[1.0], [0.0]])
    a1, b1 = torch.tensor([[0.0, 1.0]]), torch.tensor([[0.0], [1.0]])
    stock, tuned = {"weight": base + b0 @ a0}, {"weight": base + b1 @ a1}
    assert torch.equal(interpolate_state(stock, tuned, 0)["weight"], stock["weight"])
    assert torch.equal(interpolate_state(stock, tuned, 1)["weight"], tuned["weight"])
    mixed = interpolate_state(stock, tuned, 0.5)["weight"]
    assert torch.equal(mixed, base + 0.5 * (b0 @ a0 + b1 @ a1))
    assert not torch.equal(mixed, base + ((b0 + b1) / 2) @ ((a0 + a1) / 2))
    with pytest.raises(ValueError, match="names"):
        interpolate_state(stock, {"different": tuned["weight"]}, 0.5)


def test_checkpoint_export_survives_destructive_upstream_serialization(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    from dataclasses import dataclass, field
    from types import ModuleType
    from safetensors.torch import save_file
    from intent_training.kevpatch.interpolate import export_checkpoint

    @dataclass
    class Meta:
        base: str = "fixture"
        base_revision: str = "fixture"
        head_dim: int = 2
        option_isolation: bool = False
        lora: int = 1
        weights: str = "lora"
        weights_dtype: str = "fp32"
        temperature: float = 1.0
        head: dict = field(default_factory=dict)
        extra: dict = field(default_factory=dict)

    class Backbone(torch.nn.Linear):
        def save_pretrained(self, destination, *, state_dict, max_shard_size):
            save_file(dict(state_dict), str(destination / "model.safetensors"))
            state_dict.clear()

    class Tokenizer:
        def save_pretrained(self, destination):
            (destination / "tokenizer.json").write_text("{}")

    class Checkpoint:
        def __init__(self, path):
            self.meta = Meta()

        def load(self, device, options):
            torch.manual_seed(3)
            model = SimpleNamespace(lm=Backbone(2, 2), head=torch.nn.Linear(2, 2))
            return Tokenizer(), model

    module = ModuleType("kev.checkpoint")
    module.Checkpoint = Checkpoint
    module.LoadOptions = lambda **kwargs: kwargs
    module.write_meta = lambda destination, meta: torch.save({"head": meta.head}, destination / "head.pt")
    monkeypatch.setitem(sys.modules, "kev.checkpoint", module)
    evidence = export_checkpoint("stock", "tuned", 0, tmp_path / "export")
    assert evidence["backbone_tensors"] > 0
    assert evidence["head_tensors"] > 0
    assert evidence["alpha_zero_tensor_identity"]
    assert evidence["written_tensor_identity"]
