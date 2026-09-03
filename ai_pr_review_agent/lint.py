"""Lint/static check module for ai-pr-review-agent."""

import argparse
import sys
from pathlib import Path


def check_trailing_whitespace():
    """Check for trailing whitespace in Python files."""
    errors = 0
    for file_path in Path(".").rglob("*.py"):
        if any(part.startswith(".") for part in file_path.parts):
            continue
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line != line.rstrip():
                errors += 1
    return errors


def check_import_sort():
    """Check that imports are sorted (stub)."""
    return 0


def main():
    """Run mechanical lint checks."""
    parser = argparse.ArgumentParser(description="AI PR Review Agent — lint PR")
    parser.add_argument("--pr", required=True, help="PR identifier (e.g., number or URL)")
    parser.parse_args()

    # Run checks
    tw_errors = check_trailing_whitespace()
    is_errors = check_import_sort()

    total_errors = tw_errors + is_errors

    if total_errors == 0:
        print("All lint checks passed.")
        sys.exit(0)
    else:
        print(f"Lint checks found {total_errors} issue(s).")
        sys.exit(1)


if __name__ == "__main__":
    main()
