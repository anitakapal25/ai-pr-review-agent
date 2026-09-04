"""Route findings without granting mutation or merge authority."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

CONFIDENCE_HIGH = 0.75
CONFIDENCE_LOW = 0.5
IRREVERSIBLE_KEYWORDS = (
    "secret", "credential", "password", "token", "api_key", "access revoke",
    "permission revoke", "security control", "disable", "remove", "delete", "purge",
)
CRITICAL_KEYWORDS = (
    "authentication", "authorization", "login", "session", "data leak", "exposure",
    "privacy", "pii",
)


def classify_finding(finding: dict[str, Any]) -> tuple[str, str]:
    confidence = float(finding.get("confidence", 0.0))
    searchable = " ".join(
        (str(finding.get("title", "")), str(finding.get("reviewer_notes", "")))
    ).lower()
    for keyword in IRREVERSIBLE_KEYWORDS:
        if keyword in searchable:
            return "irreversible", f"irreversible-action keyword detected: {keyword}"
    for keyword in CRITICAL_KEYWORDS:
        if keyword in searchable:
            return "critical", f"critical-risk keyword detected: {keyword}"
    if confidence < CONFIDENCE_LOW:
        return "uncertain", f"confidence {confidence:.2f} is below {CONFIDENCE_LOW:.2f}"
    if confidence >= CONFIDENCE_HIGH:
        return "certain", f"confidence {confidence:.2f} meets {CONFIDENCE_HIGH:.2f}"
    return "uncertain", f"confidence {confidence:.2f} requires human verification"


def route_finding(finding: dict[str, Any]) -> dict[str, Any]:
    classification, reason = classify_finding(finding)
    requires_human = classification in {"uncertain", "critical", "irreversible"}
    action = "escalate" if requires_human else "comment"
    return {
        "classification": classification,
        "action": action,
        "requires_human": requires_human,
        "auto_apply": False,
        "audit_entry": {
            "finding_title": finding.get("title", "unknown"),
            "classification": classification,
            "reason": reason,
            "confidence": finding.get("confidence", 0.0),
            "action_taken": action,
            "requires_human": requires_human,
            "timestamp": datetime.now(UTC).isoformat(),
            "evidence_chain": finding.get("evidence_chain", []),
        },
    }
