"""Command-line orchestration for local use and CI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from ai_pr_review_agent.github import GitHubClient
from ai_pr_review_agent.models import PullRequest
from ai_pr_review_agent.publisher import publish_summary
from ai_pr_review_agent.reviewer import review_pull_request
from ai_pr_review_agent.router import route_finding
from ai_pr_review_agent.storage import artifact_path, read_json, write_json

INGEST_DIR = Path("ingested")


def _client() -> GitHubClient:
    return GitHubClient(os.environ.get("GITHUB_TOKEN", ""))


def _load_pr(number: int) -> PullRequest:
    return PullRequest.from_dict(read_json(artifact_path(INGEST_DIR, number, "metadata")))


def _load_list(number: int, kind: str) -> list[dict[str, Any]]:
    value = read_json(artifact_path(INGEST_DIR, number, kind))
    if not isinstance(value, list):
        raise TypeError(f"{kind} artifact must be a JSON array")
    return value


def command_ingest(args):
    pr = _client().get_pull_request(args.repo, args.pr)
    write_json(artifact_path(INGEST_DIR, args.pr, "metadata"), pr.to_dict())
    print(f"Ingested {args.repo}#{args.pr}: {len(pr.files)} changed file(s).")


def command_review(args):
    findings = [item.to_dict() for item in review_pull_request(_load_pr(args.pr))]
    write_json(artifact_path(INGEST_DIR, args.pr, "findings"), findings)
    print(json.dumps(findings, indent=2, ensure_ascii=False))


def command_route(args):
    routes = []
    for finding in _load_list(args.pr, "findings"):
        routes.append({"finding_title": finding.get("title", "unknown"), **route_finding(finding)})
    write_json(artifact_path(INGEST_DIR, args.pr, "routes"), routes)
    print(json.dumps(routes, indent=2, ensure_ascii=False))


def command_publish(args):
    outcome = publish_summary(
        _client(),
        args.repo,
        args.pr,
        _load_list(args.pr, "findings"),
        _load_list(args.pr, "routes"),
    )
    print(f"GitHub review summary {outcome}.")


def _run_genesis(args):
    from ai_pr_review_agent.genesis import main as genesis_main

    genesis_main(args.genesis_args)


def build_parser():
    parser = argparse.ArgumentParser(prog="pr-review", description="Evidence-grounded PR reviewer")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--repo", required=True)
    ingest.add_argument("--pr", type=int, required=True)
    ingest.set_defaults(handler=command_ingest)
    for name, handler in (("review", command_review), ("route", command_route)):
        command = commands.add_parser(name)
        command.add_argument("--pr", type=int, required=True)
        command.set_defaults(handler=handler)
    publish = commands.add_parser("publish")
    publish.add_argument("--repo", required=True)
    publish.add_argument("--pr", type=int, required=True)
    publish.set_defaults(handler=command_publish)
    genesis = commands.add_parser("genesis")
    genesis.add_argument("genesis_args", nargs=argparse.REMAINDER)
    genesis.set_defaults(handler=_run_genesis)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except (OSError, ValueError, RuntimeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
