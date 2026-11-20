"""Install the checked persistence extensions into an installed Kev package."""

from pathlib import Path

from .apply import patch_training_source


def main() -> None:
    """Patch the installed trainer while preserving the pinned package's other files."""
    import kev
    source = Path(kev.__file__).parent / "train.py"
    source.write_text(patch_training_source(source.read_text(encoding="utf-8")), encoding="utf-8")
    print("Installed checked trainer extensions.")


if __name__ == "__main__":
    main()
