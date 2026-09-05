"""Idempotent GitHub inline review and summary publication."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ai_pr_review_agent.github import GitHubClient
from ai_pr_review_agent.models import Finding

SUMMARY_MARKER = "<!-- ai-pr-review-agent:summary -->"
FINGERPRINT_PATTERN = re.compile(r"<!-- ai-pr-review-agent:fingerprint=([a-f0-9]{24}) -->")
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class PublicationResult:
    posted: int
    updated: int
    duplicates: int
    overflow: int
    summary_action: str


def render_inline_comment(finding: Finding, classification: str) -> str:
    return "\n".join(
        [
            f"**{finding.title}** (`{finding.rule_id}` · {finding.severity})",
            "",
            finding.reviewer_notes,
            "",
            f"Confidence: `{finding.confidence:.2f}` · Routing: `{classification}`",
            f"<!-- ai-pr-review-agent:fingerprint={finding.fingerprint} -->",
        ]
    )


def render_summary(
    findings: list[dict[str, Any]] | list[Finding],
    routes: list[dict[str, Any]],
    *,
    reviewed_files: int = 0,
    skipped_files: tuple[str, ...] = (),
    posted: int = 0,
    duplicates: int = 0,
    overflow: int = 0,
    head_sha: str = "unknown",
) -> str:
    lines = [SUMMARY_MARKER, "## AI PR Review", ""]
    lines += [
        f"Reviewed head: `{head_sha}`",
        f"Files reviewed: {reviewed_files}",
        f"Inline findings posted: {posted}",
        f"Duplicates suppressed: {duplicates}",
        f"Overflow findings summarized: {overflow}",
    ]
    if skipped_files:
        lines += ["", "Files skipped because GitHub did not provide a patch:"]
        lines.extend(f"- `{path}`" for path in skipped_files)
    if overflow:
        lines += [
            "",
            "Additional findings were omitted from inline publication by the configured cap.",
        ]
    if not findings:
        lines += ["", "No supported issues were found in the added lines."]
    lines += ["", "_Comment-only review. No code was changed by the agent._"]
    return "\n".join(lines)


def _upsert_summary(client: GitHubClient, repository: str, number: int, body: str) -> str:
    existing = next(
        (
            comment
            for comment in client.list_issue_comments(repository, number)
            if SUMMARY_MARKER in str(comment.get("body", ""))
        ),
        None,
    )
    if existing:
        client.update_issue_comment(repository, int(existing["id"]), body)
        return "updated"
    client.create_issue_comment(repository, number, body)
    return "created"


def publish_review(
    client: GitHubClient,
    repository: str,
    pr_number: int,
    head_sha: str,
    findings: list[Finding],
    routes: list[dict[str, Any]],
    *,
    reviewed_files: int,
    skipped_files: tuple[str, ...],
    max_comments: int,
) -> PublicationResult:
    route_by_fingerprint = {item["fingerprint"]: item for item in routes}
    ordered = sorted(
        findings,
        key=lambda item: (
            SEVERITY_ORDER.get(item.severity, 99),
            -item.confidence,
            item.path,
            item.line,
        ),
    )
    selected, overflow_findings = ordered[:max_comments], ordered[max_comments:]
    existing_by_fingerprint: dict[str, dict[str, Any]] = {}
    for comment in client.list_review_comments(repository, pr_number):
        match = FINGERPRINT_PATTERN.search(str(comment.get("body", "")))
        if match:
            existing_by_fingerprint[match.group(1)] = comment

    new_comments: list[dict[str, Any]] = []
    updated = 0
    duplicates = 0
    for finding in selected:
        route = route_by_fingerprint.get(finding.fingerprint, {})
        body = render_inline_comment(finding, str(route.get("classification", "unrouted")))
        existing = existing_by_fingerprint.get(finding.fingerprint)
        if existing:
            if str(existing.get("body", "")) != body:
                client.update_review_comment(repository, int(existing["id"]), body)
                updated += 1
            else:
                duplicates += 1
            continue
        new_comments.append(
            {"path": finding.path, "line": finding.line, "side": finding.side, "body": body}
        )

    if new_comments:
        client.create_review(
            repository,
            pr_number,
            head_sha,
            new_comments,
            "AI PR Review posted evidence-grounded inline findings.",
        )
    summary = render_summary(
        findings,
        routes,
        reviewed_files=reviewed_files,
        skipped_files=skipped_files,
        posted=len(new_comments),
        duplicates=duplicates,
        overflow=len(overflow_findings),
        head_sha=head_sha,
    )
    summary_action = _upsert_summary(client, repository, pr_number, summary)
    return PublicationResult(
        len(new_comments), updated, duplicates, len(overflow_findings), summary_action
    )


def publish_summary(
    client: GitHubClient,
    repository: str,
    pr_number: int,
    findings: list[dict[str, Any]],
    routes: list[dict[str, Any]],
) -> str:
    """Backward-compatible summary-only publisher."""
    return _upsert_summary(client, repository, pr_number, render_summary(findings, routes))


MARKER = SUMMARY_MARKER
