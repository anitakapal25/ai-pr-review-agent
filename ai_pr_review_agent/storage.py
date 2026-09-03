"""Safe persistence for normalized PR artifacts and findings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def artifact_path(root: Path, pr_number: int, kind: str) -> Path:
    if pr_number <= 0:
        raise ValueError("PR number must be positive")
    if kind not in {"metadata", "findings", "routes"}:
        raise ValueError("unsupported artifact kind")
    resolved_root = root.resolve()
    candidate = (resolved_root / f"pr_{pr_number}_{kind}.json").resolve()
    if candidate.parent != resolved_root:
        raise ValueError("artifact path escapes storage root")
    return candidate


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
