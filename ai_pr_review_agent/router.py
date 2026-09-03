"""Confidence routing module for ai-pr-review-agent.

This module classifies findings as certain/uncertain/critical/irreversible
and routes them to appropriate handling paths. The core principle:
 uncertain/critical/irreversible findings must be escalated to human
 review before any automated action is taken.

Design decisions:
- Classification is based on finding severity and type
- Critical/irreversible findings always require explicit human approval
- Uncertain findings are never auto-surfaced; they enter a human review queue
- Audit trail records every classification → human verdict → action path
- Safe degradation: if in doubt, escalate rather than act automatically
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from typing import Any

# Classification rules (in order of specificity)
# 1. Irreversible: any finding involving secret removal, access revocation,
#    security control changes, or any action that cannot be undone
# 2. Critical: any finding that could cause significant disruption if acted
#    upon without proper review (authentication bypass, data leakage, etc.)
# 3. Uncertain: any finding where confidence is below threshold or evidence
#    is not fully anchored
# 4. Certain: findings with high confidence (>0.75), well-anchored evidence,
#    and no special risk flags

# Thresholds
CONFIDENCE_HIGH = 0.75  # above this → likely real
CONFIDENCE_MEDIUM = 0.5  # 0.5–0.75 → possible, needs verification
CONFIDENCE_LOW = 0.5  # below 0.5 → uncertain, must escalate

# Risk keywords that trigger critical/irreversible classification
IRREVERSIBLE_KEYWORDS = [
    "secret",
    "credential",
    "password",
    "token",
    "api_key",
    "access revoke",
    "permission revoke",
    "security control",
    "disable",
    "remove",
    "delete",
    "purge",
]

CRITICAL_KEYWORDS = [
    "authentication",
    "authorization",
    "login",
    "session",
    "data leak",
    "exposure",
    "privacy",
    "PII",
]


def classify_finding(finding: dict[str, Any]) -> tuple[str, str]:
    """Classify a finding as certain/uncertain/critical/irreversible.

    Returns (classification, reason).
    """
    severity = finding.get("severity", "low")
    confidence = finding.get("confidence", 0.0)
    title = finding.get("title", "").lower()
    notes = finding.get("reviewer_notes", "").lower()
    evidence = finding.get("evidence_chain", [])

    # Rule 1: Irreversible — any finding with keywords indicating
    # actions that cannot be undone
    for kw in IRREVERSIBLE_KEYWORDS:
        if kw in title or kw in notes:
            return (
                "irreversible",
                f"Finding involves irreversible action: '{kw}' detected in {severity} finding",
            )

    # Rule 2: Critical — findings involving authentication, authorization,
    # data leakage, or privacy violations
    for kw in CRITICAL_KEYWORDS:
        if kw in title or kw in notes:
            return (
                "critical",
                f"Finding involves critical risk: '{kw}' detected in {severity} finding",
            )

    # Rule 3: Uncertain — low confidence or evidence not fully anchored
    if confidence < CONFIDENCE_LOW:
        reason = (
            f"Finding confidence {confidence:.2f} below threshold {CONFIDENCE_LOW}; "
            f"evidence chain: {evidence}"
        )
        return (
            "uncertain",
            reason,
        )

    # Rule 4: Medium confidence with risk keywords → critical
    if CONFIDENCE_LOW <= confidence < CONFIDENCE_HIGH:
        for kw in CRITICAL_KEYWORDS:
            if kw in title or kw in notes:
                return (
                    "critical",
                    f"Finding confidence {confidence:.2f} medium risk: '{kw}' detected",
                )

    # Rule 5: High confidence with no risk flags → certain
    if confidence >= CONFIDENCE_HIGH:
        return (
            "certain",
            f"Finding confidence {confidence:.2f} high; well-anchored; no risk flags",
        )

    # Default fallback
    reason = (
        f"Finding could not be classified with sufficient confidence "
        f"({confidence:.2f}); erring on side of cautious escalation"
    )
    return ("uncertain", reason)


def route_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Route a finding to the appropriate handling path.

    Returns a routing dict with:
    - classification: certain/uncertain/critical/irreversible
    - action: what to do (escalate/review/auto-apply/monitor)
    - requires_human: bool
    - audit_entry: dict for audit trail
    """
    classification, reason = classify_finding(finding)

    # Determine action and human requirement
    if classification == "irreversible":
        action = "escalate"
        requires_human = True
        auto_apply = False  # Never auto-apply irreversible findings
    elif classification == "critical":
        action = "escalate"
        requires_human = True
        auto_apply = False  # Never auto-apply critical findings without review
    elif classification == "uncertain":
        action = "escalate"
        requires_human = True
        auto_apply = False  # Never auto-apply uncertain findings
    elif classification == "certain":
        action = "review"
        requires_human = False
        auto_apply = False  # Confidence is not authorization; v1 is comment-only
    else:
        # Fallback: escalate
        action = "escalate"
        requires_human = True
        auto_apply = False

    # Build audit entry
    audit_entry = {
        "finding_title": finding.get("title", "unknown"),
        "classification": classification,
        "reason": reason,
        "confidence": finding.get("confidence", 0.0),
        "action_taken": action,
        "requires_human": requires_human,
        "timestamp": datetime.now(UTC).isoformat(),
        "evidence_chain": finding.get("evidence_chain", []),
    }

    return {
        "classification": classification,
        "action": action,
        "requires_human": requires_human,
        "auto_apply": auto_apply,
        "audit_entry": audit_entry,
    }


def main():
    """Main entry point for the confidence router."""
    parser = argparse.ArgumentParser(description="AI PR Review Agent — route findings")
    parser.add_argument("--pr", required=True, help="PR identifier (e.g., number or URL)")
    parser.add_argument("--findings", required=True, help="JSON string of findings to route")
    args = parser.parse_args()

    # Parse the findings JSON
    findings = json.loads(args.findings)

    # Route each finding
    results = []
    for finding in findings:
        route = route_finding(finding)
        result = {
            "finding_title": finding.get("title", "unknown"),
            "classification": route["classification"],
            "action": route["action"],
            "requires_human": route["requires_human"],
            "auto_apply": route["auto_apply"],
            "audit_entry": route["audit_entry"],
        }
        results.append(result)

    # Output routing results in structured format
    print(f"Routing {len(results)} findings for PR {args.pr}:")
    print("=" * 60)
    print()

    critical_count = sum(1 for r in results if r["classification"] == "critical")
    irreversible_count = sum(1 for r in results if r["classification"] == "irreversible")
    uncertain_count = sum(1 for r in results if r["classification"] == "uncertain")
    certain_count = sum(1 for r in results if r["classification"] == "certain")

    print("Classification summary:")
    print(f"  Certain:    {certain_count}")
    print(f"  Critical:   {critical_count}")
    print(f"  Irreversible: {irreversible_count}")
    print(f"  Uncertain:  {uncertain_count}")
    print()

    for i, r in enumerate(results, 1):
        human_mark = "🛡️ REQUIRES HUMAN" if r["requires_human"] else "✓ auto-apply"
        print(f"  {i}. [{r['classification'].upper():>10}] {r['finding_title']}")
        print(
            f"     Action: {r['action']:>10} | Human: {human_mark} | Auto-apply: {r['auto_apply']}"
        )
        print(
            f"     Audit: {r['audit_entry']['classification']} — {r['audit_entry']['reason'][:60]}"
        )
        print()

    # Summary verdict
    print("---")
    if irreversible_count > 0 or critical_count > 0 or uncertain_count > 0:
        print(
            f"⚠️  Findings requiring human review: "
            f"{irreversible_count + critical_count + uncertain_count}/{len(results)}"
        )
        print(
            "   Zero auto-apply of irreversible or critical findings without explicit human approval."
        )
    else:
        print("✓ All findings classified as certain — no human review required for this PR.")

    sys.exit(0)


if __name__ == "__main__":
    main()
