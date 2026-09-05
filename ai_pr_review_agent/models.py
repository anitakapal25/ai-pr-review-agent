"""Typed contracts shared across provider, reviewer, router, and publisher."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
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
    side: str = "RIGHT"
    head_sha: str = ""

    @property
    def fingerprint(self) -> str:
        material = f"{self.rule_id}\0{self.path}\0{self.line}\0{self.head_sha}"
        return sha256(material.encode("utf-8")).hexdigest()[:24]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["fingerprint"] = self.fingerprint
        data["evidence_chain"] = [self.path, self.line, self.evidence]
        return data


@dataclass(frozen=True)
class ReviewResult:
    findings: tuple[Finding, ...]
    reviewed_files: int
    skipped_files: tuple[str, ...]
