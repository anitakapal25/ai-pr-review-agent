"""Human feedback collection and validation module for ai-pr-review-agent.

Collects human ratings on reviewer findings, persists them for evaluation
computation, and provides feedback-driven drift detection.

Follows the document's traceability chain:
failure mode → design decision → implementation → test → observable evidence.
"""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_pr_review_agent.evaluation import USEFULNESS_THRESHOLD

# Paths
FEEDBACK_DIR = Path(".") / "data" / "human_feedback"
FEEDBACK_DB = FEEDBACK_DIR / "feedback.jsonl"  # append-only log
RATING_SCALE = (1, 5)  # 1 = not useful, 5 = very useful


def init_feedback_db() -> None:
    """Initialize the human feedback append-only database."""
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    if not FEEDBACK_DB.exists():
        with open(FEEDBACK_DB, "w", encoding="utf-8") as f:
            f.write("[]\n")  # empty JSON array


def record_feedback(
    pr_name: str,
    finding_title: str,
    rating: int,
    comment: str = "",
    confirmed_useful: bool | None = None,
) -> None:
    """Record a human rating for a specific finding.

    Args:
        pr_name: The PR identifier (e.g. "pr_001")
        finding_title: The title of the finding being rated
        rating: Integer 1–5 per RATING_SCALE
        comment: Optional free-text comment
        confirmed_useful: Optional boolean — whether the human confirmed
            the finding was useful (overrides rating-based inference)
    """
    init_feedback_db()
    rating = int(rating)
    if rating < RATING_SCALE[0] or rating > RATING_SCALE[1]:
        raise ValueError(f"Rating must be between {RATING_SCALE[0]} and {RATING_SCALE[1]}")

    entry = {
        "pr_name": pr_name,
        "finding_title": finding_title,
        "rating": rating,
        "comment": comment,
        "confirmed_useful": confirmed_useful,
        "timestamp": __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(),
    }

    # Append to the JSONL database
    with open(FEEDBACK_DB, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def compute_usefulness_from_feedback(pr_name: str) -> float | None:
    """Compute the average usefulness rating for a PR from the feedback DB.

    Returns None if no feedback exists yet.
    """
    if not FEEDBACK_DB.exists():
        return None

    ratings: list[int] = []
    with open(FEEDBACK_DB, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Skip entries that are lists (e.g. the initial "[]") rather than dicts
                if not isinstance(entry, dict):
                    continue
                if entry.get("pr_name") == pr_name and "rating" in entry:
                    ratings.append(int(entry["rating"]))
            except (json.JSONDecodeError, ValueError):
                continue

    if not ratings:
        return None

    avg = sum(ratings) / len(ratings)
    return round(avg, 2)


def is_useful_enough(pr_name: str, threshold: float | None = None) -> bool | None:
    """Check whether the average usefulness meets the project threshold.

    Args:
        pr_name: The PR identifier
        threshold: Minimum average rating to qualify; defaults to
            USEFULNESS_THRESHOLD (3)

    Returns:
        None if no feedback exists; True/False otherwise.
    """
    avg = compute_usefulness_from_feedback(pr_name)
    if avg is None:
        return None
    threshold = threshold or USEFULNESS_THRESHOLD
    return avg >= threshold


def export_feedback_report(pr_name: str, output_path: Path | None = None) -> Path:
    """Export a human-readable feedback report for a PR.

    Args:
        pr_name: The PR identifier
        output_path: Optional path to write the report; if omitted, writes
            to data/human_feedback/report_<pr_name>.md

    Returns:
        Path to the exported report file.
    """
    init_feedback_db()

    ratings: list[dict[str, Any]] = []
    comments: list[str] = []
    with open(FEEDBACK_DB, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("pr_name") == pr_name:
                    ratings.append(entry)
                    if entry.get("comment"):
                        comments.append(entry["comment"])
            except (json.JSONDecodeError, ValueError):
                continue

    avg_rating = sum(r["rating"] for r in ratings) / len(ratings) if ratings else 0
    total = len(ratings)

    report_lines = [
        f"# Human Feedback Report: {pr_name}",
        f"- Total ratings: {total}",
        f"- Average rating: {round(avg_rating, 2)}/5",
        f"- Threshold: {USEFULNESS_THRESHOLD}/5",
        f"- Meets threshold: {avg_rating >= USEFULNESS_THRESHOLD if avg_rating else None}",
        "",
        "## Individual Ratings:",
    ]
    for i, r in enumerate(ratings, 1):
        comment_str = f' — "{r.get("comment", "")}"' if r.get("comment") else ""
        confirmed = " (confirmed useful)" if r.get("confirmed_useful") else ""
        rating_str = f"{i}. rating={r['rating']}{comment_str}{confirmed}"
        report_lines.append(rating_str)

    if comments:
        report_lines.append("")
        report_lines.append("## Comments:")
        for c in comments:
            report_lines.append(f"- {c}")

    report_lines.append("")
    report_lines.append("---")

    # Write to file
    if output_path is None:
        output_path = FEEDBACK_DIR / f"report_{pr_name}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    return output_path


# ── Convenience runner ────────────────────────────────────────────────

if __name__ == "__main__":
    init_feedback_db()
    print("Human feedback database initialized at:", FEEDBACK_DB)
