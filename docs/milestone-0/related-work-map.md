# Related-Work Map (One Page)

**Project:** InterfaceCache — tree-decomposition summaries for fast **local plan repair**  
**Question answered here:** What is new compared with **static factored planning**?

---

## Positioning in one paragraph

Prior work uses graph structure (treewidth, factoring, decoupling) mainly to **solve a fixed planning task faster offline**. We use tree decomposition to **maintain sound component summaries online** and **recompute only the region affected by an execution-time disruption**. The novelty is not “planning becomes easy at low treewidth”; it is **localized invalidation + reuse** with a **repair-time bound** tied to the affected subtree.

---

## Map

| Area | Representative directions | Typical assumption | What they optimize | Gap relative to InterfaceCache |
|------|---------------------------|--------------------|--------------------|--------------------------------|
| **Classical replanning** | Execution monitoring, plan repair after action failure (e.g., execution-aware replanning, SAMP-style monitoring) | Full state observable; repair often **re-solves globally** or patches heuristically | Valid continuation from current state | Little **structural reuse** of prior factorization; no **interface-summary cache** with **sound partial invalidation** |
| **Treewidth / graph structure in planning** | Structural decompositions of planning graphs; bounded-width DP / message passing on trees | Fixed task; decomposition built **once** | **Initial** planning time for structured instances | Does not target **incremental repair** after **local task/state change** |
| **Factored / decoupled planning** | Factored transition systems, distributed forward search, agent-based or region-based factoring | Components interact through **fixed interfaces**; summaries computed for the **static** task | Offline search or optimal coordination | Summaries are for **static** composition, not **versioned caches** invalidated by **execution disruptions** |
| **Compiling / tabulating subproblems** | Pattern databases, symbolic overlays, component abstractions | Precompute tables **before** execution | Heuristic or exact **preprocess-then-search** | Tables are not maintained under **online structural change** with proven reuse of **unaffected** components |
| **Dynamic / temporal extensions** | Event-driven replanning, contingent planning, replanning in robotics stacks | Often domain-specific or non-deterministic | Robustness under change | Lacks a **deterministic FDR fragment** with **tree-decomposition summary semantics** and **affected-subtree** complexity statement |
| **This work (InterfaceCache)** | Cached **interface transition summaries** on a **rooted tree decomposition** | Deterministic FDR fragment; cross-bag coupling only through **separators**; conservative invalidation | **Online repair time** after local disruption | **Explicit** reuse of unchanged summaries; repair bound scales with **\|T_δ\|, w_δ, s_δ** not \|T\|, w |

---

## Static factored planning vs. localized recomputation

| | Static factored planning | InterfaceCache (this project) |
|--|--------------------------|-------------------------------|
| **When structure is used** | Before / during initial solve | Before initial solve **and** during repeated repairs |
| **Summary role** | Compose subproblems to find a plan | **Cache** subproblem behavior for **reuse** |
| **Trigger for recomputation** | New task instance (usually) | **Local disruption** δ during execution |
| **Reuse unit** | Often implicit in search | **Explicit** per-bag summary tables with **dependency versions** |
| **Correctness story** | Soundness of factored search / composition | **Unaffected-summary reuse lemma** + **affected-subtree** recomputation |
| **Performance claim** | Faster planning on loosely coupled tasks | Faster **repair** when δ is local and interfaces stay small |

---

## Suggested citations to expand in the paper (not exhaustive)

- **FDR / SAS+ planning:** Helmert (Fast Downward, translation pipeline).
- **Treewidth in planning:** Gaspers et al.; Rintanen; Katz & Domshlak (structural parameters).
- **Factored / decoupled search:** Brafman & Domshlak (FACT); Nissim et al.; Torralba et al. (partially ordered planning under factoring).
- **Plan execution & repair:** Williams & Nayak; execution monitoring literature; replanning in IPC-style domains.
- **Junction trees / belief propagation:** Pearl; Dechter (reasoning on graphical models)—**analogous** interface propagation, but we target **deterministic planning summaries**, not inference.

---

## Claims we explicitly do **not** make

- All planning tasks become easy at low treewidth.
- Global optimality of repaired plans unless proven under stated costs.
- Replacement for full replanning on densely coupled tasks.
- Novelty of tree decompositions, factored planning, or decoupled search **as ideas**.

## Claim we **do** make

> Execution-time plan repair can be formulated as **localized recomputation of cached, sound interface summaries** over a tree decomposition; under a restricted deterministic fragment, repair complexity is **parameterized by the affected subtree**, not the full problem size.
