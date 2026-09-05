"""Deterministic review of added PR lines with verifiable evidence."""

from __future__ import annotations

import re
from fnmatch import fnmatch
from typing import Protocol

from ai_pr_review_agent.config import ReviewConfig
from ai_pr_review_agent.models import Finding, PullRequest, ReviewResult

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


class Analyzer(Protocol):
    """Contract shared by deterministic and future LLM analyzers."""

    def analyze(self, pr: PullRequest, config: ReviewConfig) -> ReviewResult: ...


def _excluded(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(path, pattern) or fnmatch(f"/{path}", pattern) for pattern in patterns)


def analyze_pull_request(pr: PullRequest, config: ReviewConfig | None = None) -> ReviewResult:
    config = config or ReviewConfig()
    findings: list[Finding] = []
    skipped: list[str] = []
    reviewed_files = 0
    for changed_file in pr.files:
        if _excluded(changed_file.filename, config.exclude_paths):
            continue
        if not changed_file.patch:
            skipped.append(changed_file.filename)
            continue
        reviewed_files += 1
        for line_number, line in added_lines(changed_file.patch):
            stripped = line.strip()
            if "PY001" in config.enabled_rules and re.match(r"^except\s*:\s*(#.*)?$", stripped):
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
                        "RIGHT",
                        pr.head_sha,
                    )
                )
            if (
                "SEC001" in config.enabled_rules
                and SECRET_ASSIGNMENT.search(line)
                and not stripped.startswith("#")
            ):
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
                        "RIGHT",
                        pr.head_sha,
                    )
                )
    ordered = tuple(sorted(findings, key=lambda item: (item.path, item.line, item.rule_id)))
    return ReviewResult(ordered, reviewed_files, tuple(skipped))


def review_pull_request(pr: PullRequest) -> list[Finding]:
    """Compatibility helper returning only findings."""
    return list(analyze_pull_request(pr).findings)


def validate_findings(pr: PullRequest, findings: list[Finding]) -> list[Finding]:
    """Fail closed unless every finding matches an actual added line on this head SHA."""
    added_by_path = {
        changed_file.filename: dict(added_lines(changed_file.patch))
        for changed_file in pr.files
        if changed_file.patch
    }
    for finding in findings:
        actual = added_by_path.get(finding.path, {}).get(finding.line)
        if finding.side != "RIGHT" or finding.head_sha != pr.head_sha or actual != finding.evidence:
            raise ValueError(
                f"finding {finding.rule_id} has invalid evidence at {finding.path}:{finding.line}"
            )
    return findings
