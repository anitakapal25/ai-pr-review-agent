"""Minimal GitHub REST adapter with bounded retries and strict inputs."""

from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ai_pr_review_agent.models import ChangedFile, PullRequest

REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")


class GitHubError(RuntimeError):
    """A bounded, user-readable provider failure."""


class GitHubClient:
    def __init__(self, token: str, *, timeout: float = 15.0, retries: int = 2) -> None:
        if not token:
            raise ValueError("GITHUB_TOKEN is required")
        self.token = token
        self.timeout = timeout
        self.retries = retries

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        if not path.startswith("/") or ".." in path:
            raise ValueError("invalid GitHub API path")
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            "https://api.github.com" + path,
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ai-pr-review-agent/0.2",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                retryable = exc.code in {429, 500, 502, 503, 504}
                if not retryable or attempt == self.retries:
                    raise GitHubError(f"GitHub API returned HTTP {exc.code}") from exc
            except (URLError, TimeoutError) as exc:
                if attempt == self.retries:
                    raise GitHubError("GitHub API request failed or timed out") from exc
            time.sleep(0.25 * (2**attempt))
        raise GitHubError("GitHub API request failed")

    @staticmethod
    def validate_repository(repository: str) -> str:
        if not REPOSITORY_PATTERN.fullmatch(repository):
            raise ValueError("repository must have OWNER/NAME format")
        return repository

    def get_pull_request(self, repository: str, number: int) -> PullRequest:
        repository = self.validate_repository(repository)
        if number <= 0:
            raise ValueError("PR number must be positive")
        raw = self._request("GET", f"/repos/{repository}/pulls/{number}")
        if (
            not isinstance(raw, dict)
            or not isinstance(raw.get("base"), dict)
            or not isinstance(raw.get("head"), dict)
        ):
            raise GitHubError("GitHub returned an invalid pull request response")

        files: list[ChangedFile] = []
        page = 1
        while True:
            query = urlencode({"per_page": 100, "page": page})
            raw_files = self._request("GET", f"/repos/{repository}/pulls/{number}/files?{query}")
            if not isinstance(raw_files, list):
                raise GitHubError("GitHub returned an invalid changed-files response")
            files.extend(ChangedFile.from_dict(item) for item in raw_files)
            if len(raw_files) < 100:
                break
            page += 1
            if page > 30:
                raise GitHubError("PR exceeds the supported 3,000-file review limit")

        return PullRequest(
            repository=repository,
            number=number,
            title=str(raw.get("title", "")),
            body=str(raw.get("body") or ""),
            base_sha=str(raw["base"].get("sha", "")),
            head_sha=str(raw["head"].get("sha", "")),
            html_url=str(raw.get("html_url", "")),
            files=tuple(files),
        )

    def list_issue_comments(self, repository: str, number: int) -> list[dict[str, Any]]:
        repository = self.validate_repository(repository)
        result = self._request("GET", f"/repos/{repository}/issues/{number}/comments?per_page=100")
        if not isinstance(result, list):
            raise GitHubError("GitHub returned an invalid comments response")
        return result

    def create_issue_comment(self, repository: str, number: int, body: str) -> dict[str, Any]:
        return self._request(
            "POST", f"/repos/{repository}/issues/{number}/comments", {"body": body}
        )

    def update_issue_comment(self, repository: str, comment_id: int, body: str) -> dict[str, Any]:
        return self._request(
            "PATCH", f"/repos/{repository}/issues/comments/{comment_id}", {"body": body}
        )

    def list_review_comments(self, repository: str, number: int) -> list[dict[str, Any]]:
        repository = self.validate_repository(repository)
        comments: list[dict[str, Any]] = []
        page = 1
        while True:
            query = urlencode({"per_page": 100, "page": page})
            result = self._request("GET", f"/repos/{repository}/pulls/{number}/comments?{query}")
            if not isinstance(result, list):
                raise GitHubError("GitHub returned an invalid review-comments response")
            comments.extend(item for item in result if isinstance(item, dict))
            if len(result) < 100:
                return comments
            page += 1

    def create_review(
        self,
        repository: str,
        number: int,
        head_sha: str,
        comments: list[dict[str, Any]],
        body: str,
    ) -> dict[str, Any]:
        repository = self.validate_repository(repository)
        payload = {
            "commit_id": head_sha,
            "event": "COMMENT",
            "body": body,
            "comments": comments,
        }
        return self._request("POST", f"/repos/{repository}/pulls/{number}/reviews", payload)

    def update_review_comment(self, repository: str, comment_id: int, body: str) -> dict[str, Any]:
        repository = self.validate_repository(repository)
        return self._request(
            "PATCH", f"/repos/{repository}/pulls/comments/{comment_id}", {"body": body}
        )
