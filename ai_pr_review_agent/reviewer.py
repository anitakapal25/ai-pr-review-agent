"""Deterministic review of added PR lines with verifiable evidence."""

from __future__ import annotations

import re
from pathlib import Path

from ai_pr_review_agent.models import Finding, PullRequest
from ai_pr_review_agent.storage import artifact_path, read_json

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|password|secret|token)\b\s*=\s*['\"][^'\"]{8,}['\"]"
)


def added_lines(patch: str):
    """Yield (new-file line number, text) from a unified diff patch."""
    new_line: int | None = None
    for raw_line in patch.splitlines():
        match = HUNK_HEADER.match(raw_line)
        if match:
            new_line = int(match.group(1))
            continue
        if new_line is None or raw_line.startswith("\\ No newline"):
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            yield new_line, raw_line[1:]
            new_line += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            continue
        else:
            new_line += 1


def review_pull_request(pr: PullRequest) -> list[Finding]:
    findings: list[Finding] = []
    for changed_file in pr.files:
        if not changed_file.patch:
            continue
        for line_number, line in added_lines(changed_file.patch):
            stripped = line.strip()
            if re.match(r"^except\s*:\s*(#.*)?$", stripped):
                findings.append(
                    Finding(
                        "PY001",
                        "Bare except clause",
                        "medium",
                        0.99,
                        changed_file.filename,
                        line_number,
                        line,
                        "Catch an explicit exception type so cancellation and exit signals propagate.",
                    )
                )
            if SECRET_ASSIGNMENT.search(line) and not stripped.startswith("#"):
                findings.append(
                    Finding(
                        "SEC001",
                        "Potential hardcoded credential",
                        "high",
                        0.9,
                        changed_file.filename,
                        line_number,
                        line,
                        "Remove the value from source and rotate it if it is active.",
                    )
                )
    return sorted(findings, key=lambda item: (item.path, item.line, item.rule_id))


def generate_findings(pr_id: str) -> list[dict]:
    """Compatibility API: load an ingested PR and return serializable findings."""
    try:
        number = int(pr_id)
    except ValueError as exc:
        raise ValueError("PR identifier must be a positive integer") from exc
    metadata = read_json(artifact_path(Path("ingested"), number, "metadata"))
    return [finding.to_dict() for finding in review_pull_request(PullRequest.from_dict(metadata))]
