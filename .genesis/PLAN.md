# Lifecycle Plan — AI PR Review Agent

Operational status is canonical in `state.yaml`; this document explains sequencing and intent.
Milestones can be marked complete only when their demo, quality commands, evidence artifacts, and an
independent verification verdict are recorded.

## Architectural choice

The project uses a GitHub-native interface around a provider-independent CLI core. This avoids a
premature custom UI, keeps review feedback where developers already work, and lets local tests exercise
the same domain pipeline as CI. Deterministic checks precede any future LLM analysis; all findings pass
through evidence validation and policy routing before publication. See ADR-0001.

## Ordered milestones

1. **M0 — Genesis lifecycle repair:** establish valid intent, graph, milestone state, and checks.
2. **M1 — Package and CLI foundation:** installable package, unified commands, models, and tests.
3. **M2 — Real GitHub ingestion:** authenticated, paginated, bounded ingestion of normalized PR data.
4. **M3 — Review engine:** analyze added lines and emit verifiable, typed findings.
5. **M4 — GitHub publishing:** create or update one comment-only review summary.
6. **M5 — Evaluation and production readiness:** expand rules/LLM support only behind measured quality gates.

## Current status

M0–M4 are implemented but remain `active`, not complete: this environment does not currently provide
a Python runtime, so demos and tests have not produced acceptable gate evidence. M5 remains planned.

