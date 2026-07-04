# Milestone 1 — Tiny Correct Prototype: Design

Status: approved
Date: 2026-07-03
Scope: CLAUDE.md Milestone 1 only (§17). Feeds into Milestone 2 (synthetic benchmark) and beyond, but does not attempt them.

## 1. Goal and exit criterion

Build the smallest possible correct implementation of localized-recomputation plan repair, exact enough to
differentially test against brute-force full replanning on hand-authored tiny FDR tasks.

**Exit criterion (verbatim from CLAUDE.md §17, M1):** Localized repair and full recomputation match feasibility
on all tiny exhaustive tests. This design also requires cost equality, since Phase‑1 summaries are exact/cost-optimal
by construction (§6), not merely feasibility flags.

## 2. Toy domains

Two hand-authored fixtures, both "two (or more) loosely coupled rooms sharing one separator variable":

- `tests/fixtures/two_room_basic.py` — two rooms (A, B), each with a robot-location variable and a box-location
  variable local to that room, connected only by one shared `door ∈ {open, closed}` variable. Actions in room A
  only reference room-A variables + `door`; symmetric for B. Decomposition: 2 leaf bags, 1 separator of size 1.
- `tests/fixtures/two_room_deeper.py` — room A – hallway – room B chain (3 bags), to exercise summary
  propagation through an intermediate (non-leaf, non-root) bag, not just a direct parent/child pair.

Both fixtures are small enough that all reachable states can be exhaustively enumerated by a reference BFS/Dijkstra
for differential testing.

## 3. Modules

Subset of the full CLAUDE.md §9 architecture — only what M1 needs. Everything else (IPC parsing, other baselines,
non-enumerative solvers, experiment runners, plotting) is out of scope for this milestone.

```
src/fdr/task.py                  # Variable, Action, State, Task — frozen dataclasses
src/fdr/simulator.py             # is_applicable, apply_action, validate_plan (independent plan validator)

src/graph/interaction_graph.py   # primal interaction graph over FDR variables (networkx.Graph)
src/graph/decomposition.py       # wraps networkx.algorithms.approximation.treewidth_min_fill_in,
                                  # normalizes into our own rooted TreeDecomposition (bags, parent/child, separators)
src/graph/bag_assignment.py      # assign each action to the shallowest bag covering its full scope;
                                  # deterministic tie-break by bag id

src/summaries/interface.py       # InterfaceAssignment, SummaryEntry, SummaryTable (schema per CLAUDE.md §6)
src/summaries/local_solver.py    # Phase 1: enumerative local Dijkstra over (local_state, interface) pairs
src/summaries/compose.py         # bottom-up composition: bag's local table + children's summary tables
src/summaries/cache.py           # versioned cache: bag_id -> SummaryEntry set, keyed by dependency fingerprint
src/summaries/invalidation.py    # disruption -> directly-affected bags -> Steiner tree -> ancestor propagation

src/repair/disruption.py         # Disruption: state-fact change (v := d) | action-unavailability
src/repair/localized_repair.py   # the 11-step algorithm, CLAUDE.md §7, verbatim
src/repair/full_replan.py        # brute-force BFS/Dijkstra over the whole task — reference oracle AND baseline
```

Root selection: the bag containing goal variables; ties broken by smallest separator (§5).
Bag assignment: shallowest covering bag; ties broken by bag id (§5).

## 4. Summary computation (Phase 1, exact)

For each bag, enumerate all locally reachable `(local_state, incoming_interface)` pairs reachable using only
actions owned by that bag's subtree, run a local Dijkstra to the cheapest reachable `outgoing_interface`, and
record a `SummaryEntry` (feasible, cost, local_plan_fragment, child_interface_choices, provenance) per the exact
§6 schema. `compose.py` merges a bag's local table with its children's summary tables by matching separator
assignments — this is the mechanism the summary-composition lemma (§8) needs to hold, and it must be testable
in isolation from the invalidation logic.

## 5. Disruptions supported

Per CLAUDE.md §4's initial list, only the two simplest disruption types for M1:

1. State-fact value change (`v := d`)
2. Action unavailability (an action is temporarily removed from `A`)

Resource/capacity variables, edge removal from the interaction graph, and conditional effects are deferred.

## 6. Localized repair algorithm

Implements the 11 steps in CLAUDE.md §7 verbatim: find directly affected bags → Steiner-tree expansion →
ancestor propagation when a changed separator invalidates a parent → recompute bottom-up inside the affected
subtree → reuse everything outside it → compose the root summary → extract a plan → validate independently via
`simulator.py` → fall back to `full_replan.py` and log the fallback if no feasible root summary exists.

Every repair run logs the fields listed in CLAUDE.md §16 (directly changed variables/actions, directly affected
bags, final affected subtree, reused bags, recomputed bags, boundary separators, root feasibility, fallback
occurrence, final validation result).

## 7. Testing strategy (per CLAUDE.md §15)

- **Unit**: FDR transition semantics; action ownership (assigned exactly once, owner bag covers full scope);
  separator construction; `SummaryEntry` versioning/serialization.
- **Differential (primary M1 exit-criterion test)**: for every fixture and every hand-authored disruption,
  assert `localized_repair` and `full_replan` agree on feasibility; if both return a plan, both validate via the
  independent simulator and have equal cost.
- **Property-based**: a reused summary is never reused after a declared dependency changes; a disruption with no
  path to a bag's dependencies never invalidates that bag (cache correctness, independent of plan correctness).

## 8. Explicitly out of scope for this round

IPC domain parsing/PDDL, non-enumerative local solvers (SAT/BDD), suffix-reuse and fixed-window baselines,
cache eviction/lazy materialization, cost/makespan objectives beyond basic min-cost summaries, experiment
generators, plotting, and the paper draft itself. These belong to Milestones 2–5.

## 9. Definition of done for this design

All differential tests pass on both fixtures across all hand-authored disruptions (state-fact change and
action-unavailability), with full CLAUDE.md §16 logging present on every repair run, before this milestone is
considered complete.
