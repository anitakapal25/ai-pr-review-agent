# AI PR Review Agent

An evidence-grounded PR reviewer that uses GitHub itself as the user interface. The agent ingests
changed files, reviews added diff lines, routes risky or uncertain findings to humans, and can publish
a single idempotent review summary. It never changes repository code.

## Why there is no custom UI

Developers already work in pull requests. GitHub provides authentication, permissions, inline code,
conversation, checks, and audit history. A separate dashboard would duplicate those capabilities
before there is evidence it is needed. The CLI is retained for local debugging and CI composition.

See [ARCHITECTURE.md](ARCHITECTURE.md) and `.genesis/decisions/0001-github-native-cli-core.md`
for the architectural reasoning.

## Local usage

Python 3.11 or newer is required.

```shell
python -m ai_pr_review_agent ingest --repo OWNER/REPOSITORY --pr 123
python -m ai_pr_review_agent review --pr 123
python -m ai_pr_review_agent route --pr 123
python -m ai_pr_review_agent publish --repo OWNER/REPOSITORY --pr 123
python -m ai_pr_review_agent genesis check
```

Set `GITHUB_TOKEN` for GitHub operations. Ingested data and generated findings are written under
`ingested/`, which is intentionally ignored by Git.

## Use from another repository

After release `v1.0.0` is verified and tagged, add this workflow to each owned repository:

```yaml
name: Central PR Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    uses: anitakapal25/ai-pr-review-agent/.github/workflows/reusable-pr-review.yml@v1.0.0
```

Optionally add `pr-review.yaml` at the target repository root. Supported fields are
`enabled_rules`, `exclude_paths`, and `max_inline_comments`. The central workflow cap always wins
when it is lower than the repository setting.

## Safety defaults

- PR text and patches are untrusted data.
- Only GitHub API HTTPS endpoints are contacted.
- Review operates on added diff lines, not arbitrary paths supplied by PR content.
- Publishing creates or updates one summary comment; it does not apply patches.
- Verified findings are posted against added lines as a grouped `COMMENT` review.
- Critical, uncertain, and irreversible findings always require human review.

## Tests

```shell
python -m unittest discover -s tests -v
python -m ai_pr_review_agent genesis check
```

