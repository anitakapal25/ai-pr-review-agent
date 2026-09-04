"""Command-line orchestration for the central reusable reviewer."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ai_pr_review_agent.config import load_config
from ai_pr_review_agent.github import GitHubClient
from ai_pr_review_agent.publisher import publish_review
from ai_pr_review_agent.reviewer import analyze_pull_request, validate_findings
from ai_pr_review_agent.router import route_finding
from ai_pr_review_agent.storage import artifact_path, write_json

INGEST_DIR = Path("ingested")


def command_run(args: argparse.Namespace) -> None:
    client = GitHubClient(os.environ.get("GITHUB_TOKEN", ""))
    pull_request = client.get_pull_request(args.repo, args.pr)
    if pull_request.head_sha != args.head_sha:
        raise ValueError("PR head changed; retry against the latest commit")
    config = load_config(Path(args.config) if args.config else None, workflow_max=args.max_comments)
    review = analyze_pull_request(pull_request, config)
    findings = validate_findings(pull_request, list(review.findings))
    routes = [
        {
            "finding_title": finding.title,
            "fingerprint": finding.fingerprint,
            **route_finding(finding.to_dict()),
        }
        for finding in findings
    ]
    write_json(artifact_path(INGEST_DIR, args.pr, "metadata"), pull_request.to_dict())
    write_json(
        artifact_path(INGEST_DIR, args.pr, "findings"),
        [finding.to_dict() for finding in findings],
    )
    write_json(artifact_path(INGEST_DIR, args.pr, "routes"), routes)
    if not args.publish:
        print(json.dumps([finding.to_dict() for finding in findings], indent=2))
        return
    result = publish_review(
        client,
        args.repo,
        args.pr,
        pull_request.head_sha,
        findings,
        routes,
        reviewed_files=review.reviewed_files,
        skipped_files=review.skipped_files,
        max_comments=config.max_inline_comments,
    )
    print(
        f"Review published: {result.posted} inline, {result.updated} updated, "
        f"{result.duplicates} duplicates, {result.overflow} overflow."
    )


def run_genesis(args: argparse.Namespace) -> None:
    from ai_pr_review_agent.genesis import main as genesis_main

    genesis_main(args.genesis_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pr-review", description="Central PR reviewer")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--repo", required=True)
    run.add_argument("--pr", type=int, required=True)
    run.add_argument("--head-sha", required=True)
    run.add_argument("--config", default="pr-review.yaml")
    run.add_argument("--max-comments", type=int, default=20)
    run.add_argument("--publish", action="store_true")
    run.set_defaults(handler=command_run)
    genesis = commands.add_parser("genesis")
    genesis.add_argument("genesis_args", nargs=argparse.REMAINDER)
    genesis.set_defaults(handler=run_genesis)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
