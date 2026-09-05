# ADR 0002 — Reusable workflow with inline GitHub reviews

- **Date:** 2026-09-03
- **Status:** accepted
- **Milestone:** M6

## Context

The repository-local summary workflow proved detection but did not scale to several repositories or
place feedback beside changed code. A GitHub App would solve distribution but introduces hosted
webhooks, asynchronous queues, tenancy, private-key custody, and operational monitoring.

## Decision

Publish v1 as a reusable workflow pinned by target repositories to immutable tag `v1.0.0`, and publish
verified findings through one grouped GitHub `COMMENT` review using path, added-line number,
`side=RIGHT`, and the reviewed head SHA.

## Consequences

- Target repositories contain only a small caller workflow and optional configuration.
- The caller grants only contents-read and pull-requests-write permissions.
- SHA-bound fingerprints make same-commit reruns idempotent and preserve new-commit history.
- Fork PRs, blocking checks, approvals, requested changes, automatic fixes, and LLM review are excluded.
- A future GitHub App may reuse the analyzer, evidence, routing, and publisher domain contracts.

## Alternatives rejected

- Copying the full workflow and code — creates upgrade drift across repositories.
- Referencing `main` — allows unreviewed central changes to affect every consumer.
- Hosted GitHub App now — unnecessary operational and credential complexity for a few owned repos.
