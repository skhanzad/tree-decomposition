# Technical Decisions — Interaction Graph and Decomposition

Status: decided (M0); implemented in M1 (`src/graph/`)

---

## Decision summary

| Choice | Decision | Rationale |
|--------|----------|-----------|
| **Interaction graph** | Primal **action-interaction graph** over FDR variables | Default in CLAUDE.md §5; edges iff two variables co-occur in some action scope; ensures action scopes lie in cliques of \(G_I\) when scopes are pairs or share bags |
| **Decomposition engine** | **NetworkX** `treewidth_min_fill_in` | Available dependency; good enough for prototype and synthetic benchmarks; no separate C++ treewidth solver required for M1–M2 |
| **Tree shape** | Deterministic **maximum-weight spanning tree** over bag intersections, rooted at goal bag | NetworkX’s returned tree tie-breaks on hash order; we rebuild from max-clique intersections for **reproducibility** (see `decomposition.py`) |
| **Root bag** | Goal-containing bag minimizing `(bag size, lexicographic variables)` | Aligns root summary with global goal (A7) |
| **Action assignment** | Shallowest covering bag; tie-break by bag id | CLAUDE.md §5; tested in `test_bag_assignment.py` |
| **Diagnostics graph** | Directed causal graph | **Deferred** — not required for M1; interaction graph drives decomposition |
| **External TD libraries** | **Not used** in v1 | `libtw`, `htd`, etc. may be evaluated in M4 ablations if decomposition quality becomes a bottleneck |

---

## Interaction graph (detailed)

**Definition:** \(G_I = (V, E_I)\)

- Nodes: all variables in the task.
- Edge \((u,v) \in E_I\) iff \(\exists a \in A\) with \(u, v \in \mathrm{scope}(a)\).

**Implementation:** `src/graph/interaction_graph.py` — `build_interaction_graph(task)`.

**Not included in v1:**

- Goal co-occurrence edges (add only if composition tests require goals to appear in non-root bags).
- Action nodes or literal-level graphs.

**Precondition for decomposition soundness:**

- Every action’s scope must be a subset of some bag in the decomposition returned for \(G_I\). Ownership assignment **raises** if an action scope is not covered by any bag.

---

## Tree decomposition pipeline (detailed)

```
Task Π
  → build_interaction_graph(Π)           # NetworkX Graph
  → treewidth_min_fill_in(G_I)           # (width, raw junction tree)
  → select root bag (goal heuristic)
  → _maximum_spanning_tree_from_root()   # deterministic tree T
  → normalize to TreeDecomposition       # Bag dataclass, parent/child, separators
```

**Implementation:** `src/graph/decomposition.py` — `build_decomposition(task, interaction_graph)`.

### Maximal-clique assumption

The spanning-tree reconstruction assumes bags from `treewidth_min_fill_in` are **maximal cliques** with no bag strictly contained in another. This holds for the **chordal** interaction graphs produced by our M1/M2 synthetic fixtures (path-like and star-like low-treewidth domains).

**Before wider-treewidth IPC domains (M3):** add an explicit assertion or clique-maximalization step if subset bags appear.

### Separator API

- `separator_to_parent(bag_id)` → \(B_t \cap B_{p(t)}\)
- `separator_to_child(bag_id, child_id)` → \(B_t \cap B_{child}\)

Used by local solver, fingerprinting, and invalidation.

---

## Alternatives considered

| Alternative | Why not chosen (v1) |
|-------------|---------------------|
| Min-fill / min-degree exact treewidth solvers | Extra native deps; NetworkX sufficient for research prototype |
| Manual decompositions only | Doesn't scale to benchmarks; keep hand decompositions only for tiny regression fixtures if needed |
| Hypergraph / dual graph decompositions | More complex; primal graph matches CLAUDE.md and standard planning interaction view |
| Trust NetworkX tree directly | Non-deterministic tie-breaking across runs broke regression tests |

---

## Package / dependency record

| Package | Version constraint | Role |
|---------|-------------------|------|
| `networkx` | `>=3.2` | Interaction graph, `treewidth_min_fill_in` |
| Python | `>=3.11` | Dataclasses, typing |

**Future (M3+):** optional SAS+ parser; Fast Downward subprocess for full-replan baseline — not part of decomposition package decision.

---

## Validation hooks

| Check | Test / location |
|-------|-----------------|
| Every action assigned once | `tests/unit/test_bag_assignment.py` |
| Goal in root bag | `build_decomposition` raises if no goal bag |
| Decomposition stability | `test_decomposition_is_stable_across_repeated_calls_for_tied_separators` |
| Running intersection (implicit) | Relies on junction-tree construction; property tests on fixtures |

---

## Reviewer-facing takeaway

We decompose the **variable interaction structure of the planning task**, not a learned abstraction. The engineering choice is **NetworkX min-fill treewidth + deterministic re-rooting**, chosen for **reproducibility** and **low integration cost**, with a documented path to swap in higher-quality decompositions later without changing summary semantics.
