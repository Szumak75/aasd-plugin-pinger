"""Test bootstrap helpers for the standalone pinger plugin repository."""

from pathlib import Path
import os
import sys


def _candidate_paths() -> list[Path]:
    """Return possible AASd host roots used for importing public APIs."""
    repo_root = Path(__file__).resolve().parents[1]
    out: list[Path] = []
    env_root = os.environ.get("AASD_ROOT")
    if env_root:
        out.append(Path(env_root))
    out.extend(
        [
            repo_root.parent / "AASd",
            repo_root.parent.parent / "AASd",
            repo_root.parent.parent.parent / "AASd",
        ]
    )
    return out


for candidate in _candidate_paths():
    if (candidate / "aasd.py").exists() and (candidate / "libs").is_dir():
        sys.path.insert(0, str(candidate))
        break
