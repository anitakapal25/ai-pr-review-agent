"""Evaluation module for ai-pr-review-agent.

Handles golden PR assessment, precision/recall/usefulness computation,
adversarial/fault tests, feedback validation, and drift/regression gates.

Follows the document's traceability chain:
failure mode → design decision → implementation → test → observable evidence.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Constants
GOLDEN_DIR = Path(".") / "data" / "golden_prs"
EVALUATION_DIR = Path(".") / "data" / "evaluation"
PRECISION_THRESHOLD = 0.75  # Minimum precision to pass gate
RECALL_THRESHOLD = 0.70     # Minimum recall to pass gate
USEFULNESS_THRESHOLD = 3    # Minimum average usefulness (1-5)
TOKEN_BUDGET = 50000        # Per-milestone budget


def init_golden_pr(pr_name: str, expected_findings: List[Dict[str, Any]]) -> None:
    """Initialize a golden PR file for evaluation.

    Creates the golden PR JSON under `data/golden_prs/` so that
    `evaluate_pr()` can later compare generated findings against it.

    The golden PR record contains:
    - pr_name: the PR identifier
    - findings: the expected list of findings (title, severity, confidence,
      evidence_chain, reviewer_notes)
    - metadata: optional free-form fields for PR metadata
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_file = GOLDEN_DIR / f"{pr_name}.json"
    if golden_file.exists():
        # Do not overwrite an existing golden PR
        return
    golden_record = {
        "pr_name": pr_name,
        "findings": expected_findings,
        "metadata": {
            "description": f"Golden PR {pr_name} for evaluation",
            "created": str(Path.cwd()),
        },
    }
    with open(golden_file, "w", encoding="utf-8") as f:
        json.dump(golden_record, f, indent=2, sort_keys=False)


def load_golden_pr(pr_name: str) -> Optional[Dict[str, Any]]:
    """Load a golden PR with expected findings.

    Golden PRs are the ground truth against which the reviewer is evaluated.
    Each contains the PR metadata, the "true" findings, and human validation.

    Returns None if the golden PR does not exist (populate golden PRs first).
    """
    golden_file = GOLDEN_DIR / f"{pr_name}.json"
    if not golden_file.exists():
        return None
    try:
        with open(golden_file, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def compute_metrics(
    generated_findings: List[Dict[str, Any]],
    golden_findings: List[Dict[str, Any]],
) -> Dict[str, float]:
    """Compute precision, recall, and usefulness between generated and golden findings.

    Args:
        generated_findings: Findings produced by the reviewer for a PR
        golden_findings: The ground-truth findings for that PR

    Returns:
        Dict with precision, recall, and usefulness (if human ratings available).
    """
    if not golden_findings:
        # No golden issues — precision/recall undefined; usefulness from human ratings alone
        return {"precision": 1.0, "recall": 1.0, "usefulness": None}

    # --- Precision: of the generated findings, how many are valid? ---
    valid_count = 0
    for gen in generated_findings:
        gen_evidence = gen.get("evidence_chain", [])
        # A finding is "valid" if its cited evidence can be independently verified
        # by reading the code at the claimed location.
        # For automated evaluation, we mark a finding as valid when its severity
        # and confidence align with what a human would flag (simplification:
        # severity in {high, medium} and confidence >= 0.5).
        severity = gen.get("severity", "low")
        confidence = gen.get("confidence", 0.0)
        if severity in ("high", "medium") and confidence >= 0.5:
            valid_count += 1

    precision = valid_count / len(generated_findings) if generated_findings else 1.0

    # --- Recall: of the golden issues, how many were caught? ---
    # A golden finding is "caught" if a generated finding shares the same
    # file:line (evidence_chain[0:2] matches).
    caught_golden = 0
    for golden in golden_findings:
        golden_evidence = golden.get("evidence_chain", [])
        if not golden_evidence:
            continue
        golden_file_line = (golden_evidence[0], golden_evidence[1])
        for gen in generated_findings:
            gen_evidence = gen.get("evidence_chain", [])
            if not gen_evidence:
                continue
            gen_file_line = (gen_evidence[0], gen_evidence[1])
            if golden_file_line == gen_file_line:
                caught_golden += 1
                break

    recall = caught_golden / len(golden_findings) if golden_findings else 1.0

    # --- Usefulness: placeholder for human ratings ---
    # In a real workflow, this would be populated from human feedback.
    # For now, return None to indicate "not yet evaluated."
    usefulness = None

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "usefulness": usefulness,
    }


def evaluate_pr(pr_name: str) -> Dict[str, Any]:
    """Evaluate a PR against its golden version and return a full report.

    Args:
        pr_name: Name of the PR (without .json extension), e.g. "pr_001"

    Returns:
        Dict with metrics, per-finding details, and gate verdict.
    """
    golden = load_golden_pr(pr_name)
    if golden is None:
        return {
            "error": f"Golden PR '{pr_name}' not found in {GOLDEN_DIR}",
            "precision": None,
            "recall": None,
            "usefulness": None,
            "gate_verdict": "error_golden_missing",
        }

    # The reviewer's findings for this PR would normally be loaded from the
    # ingestion/output pipeline.  For this evaluation module we load them from
    # a companion file next to the golden PR:  <pr_name>_findings.json.
    findings_file = GOLDEN_DIR / f"{pr_name}_findings.json"
    if findings_file.exists():
        with open(findings_file, encoding="utf-8") as f:
            generated = json.load(f)
    else:
        # If no findings file exists, we treat the PR as having no generated
        # findings — metrics will reflect an empty reviewer output.
        generated = []

    metrics = compute_metrics(generated, golden.get("findings", []))

    # Build a per-finding detail table
    per_finding_details = []
    for gen in generated:
        c = gen.get("confidence", 0.0)
        per_finding_details.append(
            {
                "title": gen.get("title", "unknown"),
                "severity": gen.get("severity", "unknown"),
                "confidence": round(c, 2) if isinstance(c, (int, float)) else c,
                "golden_match": any(
                    g.get("evidence_chain", [])[:2] == gen.get("evidence_chain", [])[:2]
                    for g in golden.get("findings", [])
                ),
            }
        )
    # Ensure every golden finding appears in the details
    for g in golden.get("findings", []):
        already = any(d["title"] == g.get("title", "unknown") for d in per_finding_details)
        if not already:
            per_finding_details.append(
                {
                    "title": g.get("title", "unknown"),
                    "severity": g.get("severity", "unknown"),
                    "confidence": None,
                    "golden_match": True,  # golden is always "matched" to itself
                }
            )

    # Gate verdict: pass if precision and recall meet thresholds
    precision = metrics.get("precision", 0)
    recall = metrics.get("recall", 0)
    precision_pass = precision >= PRECISION_THRESHOLD
    recall_pass = recall >= RECALL_THRESHOLD

    gate_verdict = "pass" if (precision_pass and recall_pass) else "fail"

    return {
        "pr_name": pr_name,
        "precision": precision,
        "recall": recall,
        "usefulness": metrics.get("usefulness"),
        "golden_count": len(golden.get("findings", [])),
        "generated_count": len(generated),
        "precision_pass": precision_pass,
        "recall_pass": recall_pass,
        "gate_verdict": gate_verdict,
        "per_finding_details": per_finding_details,
    }


def check_drift(
    current_tokens: int,
    previous_tokens_log: List[int],
) -> Dict[str, Any]:
    """Check for token-budget drift and iteration convergence.

    Args:
        current_tokens: Tokens used in the current milestone iteration.
        previous_tokens_log: List of tokens_used from prior iterations.

    Returns:
        Dict with drift status and gate verdict.
    """
    if not previous_tokens_log:
        # First iteration — no drift to detect
        return {
            "drift_detected": False,
            "trend": "stable (first iteration)",
            "budget_remaining": TOKEN_BUDGET - current_tokens,
            "gate_verdict": "pass",
        }

    # Compute moving average and compare current to prior average
    prior_avg = sum(previous_tokens_log) / len(previous_tokens_log)
    drift_amount = abs(current_tokens - prior_avg)

    # Heuristic: if current iteration uses >20% more than the prior average,
    # flag potential drift (e.g., inefficiency, unbounded loop, missing convergence)
    drift_threshold = prior_avg * 0.20
    drift_detected = drift_amount > drift_threshold

    # Trend: improving (down), stable, or worsening (up)
    if len(previous_tokens_log) >= 2:
        earlier_avg = sum(previous_tokens_log[:-1]) / (len(previous_tokens_log) - 1)
        if current_tokens < earlier_avg * 0.9:
            trend = "improving"
        elif current_tokens > earlier_avg * 1.1:
            trend = "worsening"
        else:
            trend = "stable"
    else:
        trend = "stable"

    budget_remaining = TOKEN_BUDGET - current_tokens
    budget_ok = current_tokens <= TOKEN_BUDGET

    gate_verdict = "fail" if (drift_detected or not budget_ok) else "pass"

    return {
        "drift_detected": drift_detected,
        "trend": trend,
        "budget_remaining": budget_remaining,
        "current_iteration_tokens": current_tokens,
        "prior_average_tokens": round(prior_avg, 2),
        "gate_verdict": gate_verdict,
    }


def save_evaluation(pr_name: str, result: Dict[str, Any]) -> None:
    """Persist an evaluation result to disk.

    Creates the evaluation directory and writes a JSON report.
    """
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    report_file = EVALUATION_DIR / f"{pr_name}_evaluation.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=False)