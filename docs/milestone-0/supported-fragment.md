# Supported Planning Fragment (Version 1)

This document fixes the **exact fragment** for the first soundness theorem, the M1 prototype, and initial experiments. Broader features (conditional effects, numeric fluents, partial observability) are **out of scope** until this fragment is correct and tested.

---

## Planning task

A task is a tuple

\[
\Pi = \langle V, D, A, s_0, G, c \rangle
\]

where:

| Symbol | Meaning |
|--------|---------|
| \(V\) | Finite set of state variables |
| \(D(v)\) | Finite domain of values for variable \(v\) |
| \(A\) | Finite set of **deterministic** actions |
| \(s_0\) | Initial total assignment over \(V\) |
| \(G\) | Partial goal assignment (subset of variables) |
| \(c(a) \ge 0\) | Nonnegative action cost |

Each action \(a\) has precondition \(\mathrm{pre}(a)\) and effect \(\mathrm{eff}(a)\), each a partial assignment. Applying \(a\) in state \(s\) is defined only if \(\mathrm{pre}(a) \subseteq s\); the result replaces affected variables with \(\mathrm{eff}(a)\).

---

## Fragment assumptions (all required)

### A1 — Deterministic fully observable FDR

- Transitions are deterministic.
- The agent observes the full state after every action.
- State is a total assignment to finite-domain variables.

### A2 — No conditional effects (v1)

- Each action has a single unconditional effect assignment.
- Conditional effects may be added only after v1 soundness is proven and tested.

### A3 — Nonnegative action costs

- \(c(a) \in \mathbb{Z}_{\ge 0}\) (implementation uses integers).
- Summaries record **minimum cost** over local plan fragments; ties broken deterministically in code.

### A4 — Tree decomposition over the primal interaction graph

Build an undirected **primal action-interaction graph** \(G_I\):

- Nodes: variables in \(V\).
- Edge \((u,v)\) if \(u\) and \(v\) appear together in the scope of some action.

Let \(\mathcal{T} = (T, \{B_t\}_{t \in T})\) be a **tree decomposition** of \(G_I\):

1. Every variable appears in at least one bag.
2. Every edge of \(G_I\) is contained in some bag.
3. **Running intersection:** bags containing any variable form a connected subtree of \(T\).

Root \(r \in T\) is chosen among bags covering all goal variables, tie-breaking by smaller bag size then lexicographic bag content (see implementation).

### A5 — Action ownership (single-bag scope)

Every action \(a\) is assigned to **exactly one bag** \(t\) such that \(\mathrm{scope}(a) \subseteq B_t\).

**Assignment rule (deterministic):**

1. Consider all bags whose variables contain \(\mathrm{scope}(a)\).
2. Choose the bag **closest to the root** (minimum depth).
3. Tie-break by bag id.

No action may be duplicated across bags in v1.

### A6 — Separator-only cross-bag coupling

For child bag \(t\) with parent \(p(t)\), the **separator** is

\[
S_t = B_t \cap B_{p(t)}.
\]

Information exported from the subtree rooted at \(t\) to the rest of the decomposition is **only** an assignment to \(S_t\). Local state inside the child subtree not in \(S_t\) is not exported.

### A7 — Goal locality

All goal variables appear in the root bag \(B_r\). The root summary is defined relative to the global goal assignment \(G\).

### A8 — Sound summary semantics

For each bag \(t\), the summary table entry \(\Sigma_t(i,o)\) stores the minimum cost of a **local plan fragment** owned by the subtree rooted at \(t\) that:

- starts from current global state restricted to local non-separator variables, with incoming separator assignment \(i\);
- ends with outgoing separator assignment \(o\) (or satisfies root goal when \(t = r\));
- uses only actions owned in the subtree;
- composes sound child summaries at child interfaces.

Infeasible pairs have cost \(+\infty\) / `feasible=false`.

---

## Disruption model (initial)

A disruption \(\delta\) is applied at execution time to produce post-disruption task/state \((\Pi^\delta, s^\delta)\).

**Supported in prototype (M1–M2):**

| Type | Formal effect |
|------|----------------|
| **State fact change** | \(s^\delta\) agrees with \(s\) except one variable \(v\) set to \(d \in D(v)\); task unchanged |
| **Action unavailability** | \(\Pi^\delta\) equals \(\Pi\) except action \(a\) removed from \(A\) |

**Planned but not in v1 theorem:** action failure, resource change, local edge removal.

---

## Repair problem (primary objective)

Given \((\Pi^\delta, s^\delta)\), cached summaries \(\Sigma\) for \(\Pi\), and decomposition \(\mathcal{T}\):

> Return **any** plan executable from \(s^\delta\) that satisfies \(G\), maximizing reuse of summaries whose dependencies remain valid and minimizing **online repair computation time**.

Plan **validity** is checked independently by a simulator. **Cost optimality** of repaired plans is **not** guaranteed unless the summary tables are globally cost-optimal and recomputation is complete; report cost separately from validity.

---

## Conservative invalidation policy (v1 implementation)

Let \(R_0\) be variables/actions directly changed by \(\delta\). A bag is **directly affected** if it contains a changed variable or owns a changed/unavailable action. The **affected subtree** \(T_\delta\) is the union of:

1. All directly affected bags;
2. All ancestors on paths to the root (separator propagation);
3. (Optional expansion) any bag whose child summary dependency fingerprint changes.

Recompute summaries bottom-up **only** on \(T_\delta\). Invalidate before recompute. **False-positive invalidation is acceptable; false negatives are not.**

---

## Out of scope for this fragment

- Conditional effects, derived variables, axioms
- Numeric fluents, temporal planning, nondeterminism, partial observability
- SAS+/PDDL parsing (Milestone 3)
- Learned decompositions or neural components
- Global optimality claims without proof

---

## Encoding checklist for code reviewers

| Assumption | Where enforced |
|------------|----------------|
| A1–A3 | `src/fdr/task.py`, `src/fdr/simulator.py` |
| A4 | `src/graph/interaction_graph.py`, `src/graph/decomposition.py` |
| A5 | `src/graph/bag_assignment.py` + unit tests |
| A6–A8 | `src/summaries/interface.py`, `local_solver.py`, `compose.py` |
| Disruptions | `src/repair/disruption.py` |
| Invalidation | `src/summaries/invalidation.py` |
| Repair | `src/repair/localized_repair.py` |
