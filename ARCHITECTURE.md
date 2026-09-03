# Architecture

## Flow

```text
GitHub PR event in any configured owned repository
    -> pinned reusable workflow (`v1.0.0`)
    -> GitHub adapter (authenticated fetch, timeout, schema checks)
    -> local ingestion artifact (normalized changed files and patches)
    -> deterministic reviewer (added lines only)
    -> evidence validator and confidence router
    -> GitHub summary comment (human decision remains in GitHub)
```

## Why this flow

The system uses GitHub as the interface because review discussion, identity, permissions, and line
context already live there. A CLI core keeps domain logic usable from CI and local tests without
coupling it to webhook infrastructure. Provider calls are isolated so GitLab support can be added
without changing review policy.

Deterministic checks run before any future LLM reviewer because they are cheap, explainable, and easy
to anchor to exact added lines. The `Finding` model is the boundary for future model output: an LLM
may propose findings, but the same evidence validation and routing must run before publication.

Publishing uses GitHub's line-based review API with the PR head SHA, path, new-file line, and
`side=RIGHT`. A SHA-bound fingerprint suppresses duplicate comments on reruns. New commits receive new
fingerprints so GitHub can preserve prior comments as outdated history. Automatic code changes remain
excluded because confidence is not authorization.

The workflow is reusable instead of a hosted GitHub App for v1: it centralizes implementation while
avoiding a webhook service, queue, database, and private-key custody. Each owned repository grants a
short-lived workflow token and calls an immutable release tag. Fork PRs are deferred because their
write-token security model needs a separately threat-modeled workflow.

## Trust boundaries

Repository names and PR numbers come from trusted CLI/CI configuration and are strictly validated.
PR titles, bodies, filenames, source, and patches are untrusted. They are stored as data and never
executed or interpolated into shell commands. GitHub responses must match the expected shape before
the review pipeline accepts them.

## Modules

- `github.py`: provider API boundary and retry/timeout behavior.
- `models.py`: normalized data contracts.
- `storage.py`: safe artifact naming and persistence.
- `reviewer.py`: deterministic added-line analysis and evidence anchoring.
- `router.py`: policy decisions, separate from detection.
- `publisher.py`: idempotent GitHub summary publication.
- `genesis.py`: lifecycle state validation and status reporting.

