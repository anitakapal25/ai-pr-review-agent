"""Typed contracts shared across provider, reviewer, router, and publisher."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ChangedFile:
    filename: str
    status: str
    additions: int
    deletions: int
    patch: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ChangedFile:
        filename = value.get("filename")
        if not isinstance(filename, str) or not filename or "\x00" in filename:
            raise ValueError("changed file has an invalid filename")
        return cls(
            filename=filename,
            status=str(value.get("status", "modified")),
            additions=int(value.get("additions", 0)),
            deletions=int(value.get("deletions", 0)),
            patch=value.get("patch") if isinstance(value.get("patch"), str) else None,
        )


@dataclass(frozen=True)
class PullRequest:
    repository: str
    number: int
    title: str
    body: str
    base_sha: str
    head_sha: str
    html_url: str
    files: tuple[ChangedFile, ...]

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "files": [asdict(item) for item in self.files]}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PullRequest:
        return cls(
            repository=str(value["repository"]),
            number=int(value["number"]),
            title=str(value.get("title", "")),
            body=str(value.get("body") or ""),
            base_sha=str(value["base_sha"]),
            head_sha=str(value["head_sha"]),
            html_url=str(value.get("html_url", "")),
            files=tuple(ChangedFile.from_dict(item) for item in value.get("files", [])),
        )


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    severity: str
    confidence: float
    path: str
    line: int
    evidence: str
    reviewer_notes: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_chain"] = [self.path, self.line, self.evidence]
        return data
