"""GitHub-native review summary publication."""

from __future__ import annotations

from typing import Any

from ai_pr_review_agent.github import GitHubClient

MARKER = "<!-- ai-pr-review-agent:summary -->"


def render_summary(findings: list[dict[str, Any]], routes: list[dict[str, Any]]) -> str:
    route_by_title = {item["finding_title"]: item for item in routes}
    lines = [MARKER, "## AI PR Review", ""]
    if not findings:
        lines.append("No supported issues were found in the added lines.")
    else:
        lines += [
            f"Found {len(findings)} issue(s). Validate each finding before acting.",
            "",
            "| Severity | Finding | Evidence | Routing |",
            "|---|---|---|---|",
        ]
        for finding in findings:
            evidence = finding.get("evidence_chain", ["?", 0, ""])
            route = route_by_title.get(finding.get("title"), {})
            lines.append(
                f"| {finding.get('severity', 'unknown')} | {finding.get('title', 'Untitled')} "
                f"| `{evidence[0]}:{evidence[1]}` | {route.get('classification', 'unrouted')} |"
            )
    lines += ["", "_Comment-only review. No code was changed by the agent._"]
    return "\n".join(lines)


def publish_summary(
    client: GitHubClient,
    repository: str,
    pr_number: int,
    findings: list[dict[str, Any]],
    routes: list[dict[str, Any]],
) -> str:
    body = render_summary(findings, routes)
    existing = next(
        (
            comment
            for comment in client.list_issue_comments(repository, pr_number)
            if MARKER in str(comment.get("body", ""))
        ),
        None,
    )
    if existing:
        client.update_issue_comment(repository, int(existing["id"]), body)
        return "updated"
    client.create_issue_comment(repository, pr_number, body)
    return "created"
