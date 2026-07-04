# Milestone 0 — Literature and Formal Scope

Status: complete  
Date: 2026-07-03  
Scope: CLAUDE.md §17 Milestone 0 only. Foundational documents for M1–M5; no implementation required.

## Deliverables

| Document | Purpose |
|----------|---------|
| [related-work-map.md](./related-work-map.md) | One-page map of adjacent work and the novelty gap |
| [supported-fragment.md](./supported-fragment.md) | Exact planning fragment for the first theorem and prototype |
| [theorem-draft.md](./theorem-draft.md) | Draft soundness + complexity theorems and proof outline |
| [technical-decisions.md](./technical-decisions.md) | Interaction graph and decomposition package decisions |

Canonical spec copy: [../superpowers/specs/2026-07-03-milestone-0-formal-scope.md](../superpowers/specs/2026-07-03-milestone-0-formal-scope.md)

## Exit criterion

> A reviewer can understand what is new compared with static factored planning.

**Checklist**

- [x] Related-work map names static factored / decoupled planning and states what they do *not* address (execution-time local invalidation with partial summary reuse).
- [x] Supported fragment is precise enough to encode assumptions in code and proofs.
- [x] Theorem draft separates soundness from complexity and lists proof lemmas.
- [x] Technical decisions record concrete choices already reflected in `src/graph/`.

## What is new (one sentence)

We treat **execution-time plan repair** as **localized recomputation** of **sound interface summaries** over a **tree decomposition**: after a local disruption, only an affected connected subtree is invalidated and recomputed; unchanged summaries elsewhere are reused, and repair effort is bounded by affected-subtree structure—not full task size.
