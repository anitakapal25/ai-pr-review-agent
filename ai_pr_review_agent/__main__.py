"""
Entry point for the AI PR Review Agent when invoked as a module:

    python -m ai_pr_review_agent --pr <PR_NUMBER>

The script simply forwards all arguments to the reviewer CLI.
"""

import sys
from ai_pr_review_agent.reviewer import main

if __name__ == "__main__":
    # reviewer.main() parses its own args (expects --pr) and exits with a status code.
    # We propagate that exit code back to the interpreter.
    sys.exit(main())
