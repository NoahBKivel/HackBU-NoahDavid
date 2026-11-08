"""Exercise credential detection and clean-text acceptance."""

from pathlib import Path
import subprocess
import sys


def test_detects_generated_credentials_without_printing_them(tmp_path: Path) -> None:
    sample = "sk-ant-" + "A" * 24
    target = tmp_path / "sample.txt"
    target.write_text(sample, encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "scripts" / "scan_secrets.py"
    result = subprocess.run([sys.executable, str(script), str(target)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "credential findings=1" in result.stdout
    assert sample not in result.stdout + result.stderr


def test_accepts_clean_source_text(tmp_path: Path) -> None:
    target = tmp_path / "clean.txt"
    target.write_text("No credentials occur in this sample.", encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "scripts" / "scan_secrets.py"
    result = subprocess.run([sys.executable, str(script), str(target)], capture_output=True, text=True)
    assert result.returncode == 0
    assert "credential findings=0" in result.stdout
