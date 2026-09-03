"""Validated repository-owned review configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

SUPPORTED_RULES = frozenset({"PY001", "SEC001"})
DEFAULT_EXCLUDES = ("**/vendor/**", "**/generated/**", "**/dist/**", "**/build/**")


@dataclass(frozen=True)
class ReviewConfig:
    enabled_rules: frozenset[str] = SUPPORTED_RULES
    exclude_paths: tuple[str, ...] = DEFAULT_EXCLUDES
    max_inline_comments: int = 20


def load_config(path: Path | None, *, workflow_max: int = 20) -> ReviewConfig:
    if workflow_max < 1 or workflow_max > 50:
        raise ValueError("maximum inline comments must be between 1 and 50")
    if path is None or not path.exists():
        return ReviewConfig(max_inline_comments=workflow_max)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise TypeError("review configuration must be a YAML mapping")
    allowed = {"enabled_rules", "exclude_paths", "max_inline_comments"}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError("unknown review configuration keys: " + ", ".join(sorted(unknown)))
    rules = raw.get("enabled_rules", sorted(SUPPORTED_RULES))
    excludes = raw.get("exclude_paths", list(DEFAULT_EXCLUDES))
    maximum = raw.get("max_inline_comments", workflow_max)
    if not isinstance(rules, list) or not all(isinstance(item, str) for item in rules):
        raise TypeError("enabled_rules must be a list of rule IDs")
    unsupported = set(rules) - SUPPORTED_RULES
    if unsupported:
        raise ValueError("unsupported rule IDs: " + ", ".join(sorted(unsupported)))
    if not isinstance(excludes, list) or not all(isinstance(item, str) for item in excludes):
        raise TypeError("exclude_paths must be a list of glob strings")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or not 1 <= maximum <= 50:
        raise ValueError("max_inline_comments must be an integer between 1 and 50")
    return ReviewConfig(frozenset(rules), tuple(excludes), min(maximum, workflow_max))
