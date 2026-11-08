"""Show actual refund outcomes from a completed candidate project."""

import argparse
import importlib.util
import json
import sys
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def preview(project: Path) -> dict:
    """Execute the public cancellation API on the scene's fixed example customers."""
    scene = json.loads((ROOT / "demos/refund-scene.json").read_text(encoding="utf-8"))
    name = "refund_project_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, project / "billing.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    results = []
    for example in scene["examples"]:
        subscription = module.Subscription("subscription", "charge", example["paid_cents"],
                                           date.fromisoformat(example["period_start"]), date.fromisoformat(example["period_end"]))
        payments = module.PaymentGateway()
        module.cancel_subscription("subscription", {"subscription": subscription}, payments,
                                   date.fromisoformat(example["cancel_on"]))
        refunded = sum(row["amount_cents"] for row in payments.refunds)
        results.append({"name": example["name"], "paid_cents": example["paid_cents"],
                        "actual_refund_cents": refunded, "policy_refund_cents": example["policy_refund_cents"]})
    return {"project": str(project), "examples": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(preview(args.project.resolve()), indent=2))
