"""Validate and report the repository's canonical Genesis lifecycle state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

STATE_PATH = Path(".genesis/state.yaml")
ALLOWED_STATUSES = {"planned", "active", "verifying", "complete", "blocked"}
REQUIRED_INTENT = {
    "input",
    "output",
    "autonomy",
    "human_review",
    "failure_tolerance",
    "trust_boundary",
}


def load_state(path: Path = STATE_PATH) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("Genesis state must be an object")
    return value


def validate_state(state: dict, root: Path = Path(".")) -> list[str]:
    errors: list[str] = []
    if state.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    intent = state.get("intent", {})
    missing = REQUIRED_INTENT - set(intent) if isinstance(intent, dict) else REQUIRED_INTENT
    if missing:
        errors.append("missing intent fields: " + ", ".join(sorted(missing)))
    milestones = state.get("milestones")
    if not isinstance(milestones, list) or not milestones:
        return errors + ["milestones must be a non-empty array"]
    ids: set[str] = set()
    for item in milestones:
        mid = item.get("id", "<missing>")
        if mid in ids:
            errors.append(f"duplicate milestone id: {mid}")
        ids.add(mid)
        if item.get("status") not in ALLOWED_STATUSES:
            errors.append(f"{mid}: invalid status")
        if not item.get("demo"):
            errors.append(f"{mid}: demo command is required")
        if not item.get("freeze"):
            errors.append(f"{mid}: freeze boundary is required")
        if item.get("status") == "complete" and not item.get("evidence"):
            errors.append(f"{mid}: complete milestone has no evidence")
    if state.get("active_milestone") not in ids:
        errors.append("active_milestone is unknown")
    graph_path = root / ".genesis/context-graph.json"
    if graph_path.exists():
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        if not graph.get("nodes"):
            errors.append("context graph has no module nodes")
        if len(graph.get("invariants", {})) < 2:
            errors.append("context graph needs at least two invariants")
    else:
        errors.append("context graph is missing")
    return errors


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(prog="genesis")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    commands.add_parser("status")
    args = parser.parse_args(argv)
    state = load_state()
    if args.command == "status":
        for item in state["milestones"]:
            print(f"{item['id']}: {item['status']} - {item['name']}")
        return
    errors = validate_state(state)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Genesis lifecycle state is valid.")


if __name__ == "__main__":
    main()
