# Lifecycle Plan — AI PR Review Agent

Operational status is canonical in `state.yaml`; this document explains sequencing and intent.
Milestones can be marked complete only when their demo, quality commands, evidence artifacts, and an
independent verification verdict are recorded.

## Architectural choice

The project uses a GitHub-native interface around a provider-independent CLI core. This avoids a
premature custom UI, keeps review feedback where developers already work, and lets local tests
exercise the same domain pipeline as CI. Deterministic checks precede any future LLM analysis; all
findings pass through evidence validation and policy routing before publication. See ADR-0001 and
ADR-0002.

## Ordered milestones

1. **M0 — Genesis lifecycle repair:** establish valid intent, graph, milestone state, and checks.
2. **M1 — Package and CLI foundation:** installable package, unified commands, models, and tests.
3. **M2 — Real GitHub ingestion:** authenticated, paginated, bounded ingestion of normalized PR data.
4. **M3 — Review engine:** analyze added lines and emit verifiable, typed findings.
5. **M4 — GitHub publishing:** publish added-line comments and one idempotent summary.
6. **M5 — Future analyzer evaluation:** add new analyzers only behind measured quality gates.
7. **M6 — Reusable distribution:** provide the versioned central workflow and inline publication.

## Current status

M6 is active. Its implementation and local quality gates are recorded, while release tagging and the
two-repository acceptance evidence remain outstanding. M5 remains planned for future analyzers.
