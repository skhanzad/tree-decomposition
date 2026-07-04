# Milestone 0 — Literature and Formal Scope

Status: complete  
Date: 2026-07-03  
Scope: CLAUDE.md §17 Milestone 0. Documentation only; implementation begins at M1.

## Exit criterion

> A reviewer can understand what is new compared with static factored planning.

## Deliverables

1. **Related-work map** — [docs/milestone-0/related-work-map.md](../milestone-0/related-work-map.md)  
   One-page positioning vs. static factored planning, treewidth planning, and classical replanning.

2. **Supported fragment** — [docs/milestone-0/supported-fragment.md](../milestone-0/supported-fragment.md)  
   Assumptions A1–A8, disruption types, invalidation policy, code mapping.

3. **Theorem draft** — [docs/milestone-0/theorem-draft.md](../milestone-0/theorem-draft.md)  
   Sound localized recomputation theorem, complexity contrast, Lemmas 1–4 outline.

4. **Technical decisions** — [docs/milestone-0/technical-decisions.md](../milestone-0/technical-decisions.md)  
   Primal interaction graph; NetworkX `treewidth_min_fill_in`; deterministic max-weight spanning tree re-rooting.

## Index

See [docs/milestone-0/README.md](../milestone-0/README.md).

## Downstream milestones

| Milestone | Builds on M0 |
|-----------|----------------|
| M1 | Implements fragment A1–A8 on toy tasks |
| M2 | Synthetic benchmarks testing locality / amortization |
| M3 | SAS+ tasks; decomposition quality on IPC domains |
| M4 | Full proofs of Theorem 1–2; ablations on decomposition method |
