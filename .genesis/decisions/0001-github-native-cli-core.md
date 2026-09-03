# ADR 0001 — GitHub-native interface with a CLI core

- **Date:** 2026-09-03
- **Status:** accepted
- **Phase / milestone:** M1–M4

## Context

The reviewer needs a usable interface, but a custom frontend would duplicate PR identity, permissions,
diff presentation, discussion, and resolution. Domain logic must still be testable without GitHub.

## Decision

Use GitHub comments as the initial user interface, orchestrated by a provider-independent CLI whose
network adapter, review logic, policy routing, and publishing are separate modules.

## Consequences

- Positive: users remain in their existing workflow and the core is locally testable.
- Positive: a GitLab adapter or dashboard can be added without replacing review policy.
- Negative: organization-wide analytics are deferred.
- Negative: reliable inline comments are deferred until diff-position mapping is fully tested.
- **Invariants:** provider boundary, evidence anchoring, and human authority are recorded in the context graph.

## Alternatives rejected

- Custom web UI — substantial authentication and UX work without a validated need.
- GitHub-only monolith — faster initially but couples policy and domain behavior to API payloads.
- Automatic fixes — confidence is not authorization and current evaluation evidence is insufficient.

