# In the repository root
cat > ai_pr_review_agent/__main__.py <<'EOF'
"""
Entry point for the AI PR Review Agent when run as a module:
    python -m ai_pr_review_agent --pr <PR_NUMBER>
"""
import sys
from ai_pr_review_agent.reviewer import main

if __name__ == "__main__":
    sys.exit(main())
EOF
