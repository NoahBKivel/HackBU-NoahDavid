"""Serve the intent monitor through a shared GPU container."""

import json
import os
import time
from pathlib import Path

import modal

TARGET = os.environ.get("INTENT_MONITOR_TARGET", "dev")
if TARGET not in {"dev", "live"}:
    raise ValueError("INTENT_MONITOR_TARGET must be dev or live.")
APP_NAME = "intent-monitor-dev" if TARGET == "dev" else "intent-monitor"
SESSION_NAME = f"{APP_NAME}-sessions"
MODEL_VOLUME = "intent-monitor-model-dev" if TARGET == "dev" else "intent-monitor-model"
KEV_REF = "fc4a17e194bca35a48c57211392ec49ea54a94ac"
VALIDATED_LENGTH = int(os.environ.get("INTENT_MONITOR_LENGTH", "8192"))

app = modal.App(APP_NAME)
image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .uv_pip_install(f"kev[serve] @ git+https://github.com/jaredpalmer/kev.git@{KEV_REF}",
                    "transformers==5.17.0", "peft==0.21.0")
    .uv_pip_install("flash-linear-attention==0.5.2", "triton==3.7.1")
    .uv_pip_install("pysbd")
    .env({"INTENT_MONITOR_TARGET": TARGET, "INTENT_MONITOR_LENGTH": str(VALIDATED_LENGTH), "HF_HOME": "/hf", "HF_HUB_DISABLE_PROGRESS_BARS": "1", "TOKENIZERS_PARALLELISM": "false",
          "PYTHONUNBUFFERED": "1", "TRITON_CACHE_DIR": "/hf/triton-cache"})
    .add_local_dir(Path(__file__).parent / "src" / "intent_runtime", "/root/intent_runtime")
    .add_local_dir(Path(__file__).parents[1] / "monitor_format", "/root/David/monitor_format")
)
weights = modal.Volume.from_name("intent-monitor-hf", create_if_missing=True)
model_volume = modal.Volume.from_name(MODEL_VOLUME, create_if_missing=True)
sessions = modal.Dict.from_name(SESSION_NAME, create_if_missing=True)

@app.cls(image=image, gpu="L40S", cpu=4, memory=16384,
         volumes={"/hf": weights, "/model": model_volume}, max_containers=1,
         scaledown_window=600, timeout=600, startup_timeout=1200)
@modal.concurrent(max_inputs=32)
class Classifier:
    @modal.enter()
    def load(self) -> None:
        """Load and warm the selected checkpoint with unrounded scoring."""
        import torch
        from kev.checkpoint import Checkpoint, LoadOptions
        from kev.serve import Server
        from intent_runtime.calibration import Calibrator
        from intent_runtime.model import QuestionRunner, selection
        from intent_runtime.service import Runtime
        from intent_runtime.formats import Formats
        from David import monitor_format as shared
        from intent_runtime.store import SessionStore

        started = time.time()
        chosen = selection(Path("/model"))
        checkpoint = Checkpoint(chosen["checkpoint"])
        tokenizer, model = checkpoint.load("cuda", LoadOptions(dtype=torch.bfloat16, cuda_graphs=True, fused=True, temperature=1.0))
        self.server = Server(checkpoint, tokenizer, model, "cuda")
        parameters = {}
        if chosen["calibration"]:
            calibration_path = Path(chosen["calibration"])
            if not calibration_path.is_absolute():
                calibration_path = Path("/model") / calibration_path
            parameters = json.loads(calibration_path.read_text())
        self.runner = QuestionRunner(self.server, Calibrator(parameters, checkpoint.meta.temperature))
        self.runtime = Runtime(SessionStore(sessions), self.runner, Formats(tokenizer, VALIDATED_LENGTH), chosen["source"])
        warm_text = "The user asked the agent to make the test suite faster without reducing coverage. "
        for count in (1, 4, 16):
            self.runner.ask(warm_text * count, {"M1": shared.fill_question("M1", tokenizer=tokenizer)})
        self.server.wait_idle()
        weights.commit()
        print(json.dumps({"loaded": chosen["checkpoint"], "source": chosen["source"],
                          "base": checkpoint.meta.base, "base_revision": checkpoint.meta.base_revision,
                          "shipped_temperature": checkpoint.meta.temperature, "loaded_temperature": model.head.temperature,
                          "calibration": parameters, "flag_at": 0.70,
                          "load_s": time.time() - started}), flush=True)

    @modal.method()
    def warmup(self) -> dict:
        """Return when the shared model container is ready."""
        return {"ok": True}

    @modal.method()
    def classify(self, event: dict) -> dict:
        """Judge one event and return the backend result shape."""
        self.runner.trace.requests = []
        result = self.runtime.classify(event)
        print(json.dumps({"event_id": event["event_id"], "risk": result["risk"],
                          "skipped": result["details"].get("skipped", False),
                          "probabilities": getattr(self.runner.trace, "requests", None) if result["risk"] is not None else None}), flush=True)
        return result
