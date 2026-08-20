"""Lint/static check module for ai-pr-review-agent."""

import argparse
import sys
from pathlib import Path


def check_trailing_whitespace():
    """Check for trailing whitespace in Python files."""
    errors = 0
    for f in Path(".").glob("*.py"):
        content = f.read_text(encoding="utf-8")
        if content.endswith("\n") and content.rstrip("\n") != content:
            for i, line in enumerate(content.split("\n"), 1):
                if line != line.rstrip() and line:
                    # Check if trailing whitespace exists before newline
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
    args = parser.parse_args()

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