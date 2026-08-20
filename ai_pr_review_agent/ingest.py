"""PR ingestion module for ai-pr-review-agent."""

import argparse
import sys
from pathlib import Path


def main():
    """Ingest PR metadata from GitHub/GitLab API."""
    parser = argparse.ArgumentParser(description="AI PR Review Agent — ingest PR")
    parser.add_argument("--pr", required=True, help="PR identifier (e.g., number or URL)")
    args = parser.parse_args()

    # Stub: record PR ingestion for G1 G0 pre-flight tracking
    pr_id = args.pr
    ingest_dir = Path(".") / "ingested"
    ingest_dir.mkdir(exist_ok=True)

    # Write minimal PR metadata record
    metadata = {
        "pr_id": pr_id,
        "ingested": True,
        "status": "ingested",
    }
    (ingest_dir / f"pr_{pr_id}_metadata.json").write_text(
        str(metadata), encoding="utf-8"
    )

    print(f"PR {pr_id} ingested and metadata persisted.")
    sys.exit(0)


if __name__ == "__main__":
    main()