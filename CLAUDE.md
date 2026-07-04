# CLAUDE.md — InterfaceCache: Localized Recomputation for Plan Repair

## 1. Project identity

**Working title:**
`InterfaceCache: Tree-Decomposition Summaries for Fast Local Plan Repair`

**One-sentence thesis:**
When an execution-time disruption changes only a local part of a deterministic planning task, a planner should recompute only the affected subtree of a tree decomposition, reuse sound cached summaries elsewhere, and produce a valid repaired plan faster than full replanning.

**Primary research contribution:**
A planning-and-graphs method for **localized recomputation** after execution-time failures, with reusable interface summaries and a theorem whose repair-time bound depends on the affected decomposition subtree and its interface width—not the size of the entire planning task.

**Target venue:** AAAI main technical track.

**Project style:**
Theory + systems + reproducible empirical evaluation. CPU-heavy; no neural network is required.

---

## 2. What this project is and is not

### It is

- A method for **repairing plans after local changes**.
- A method that represents a planning problem using a variable/action interaction graph and a tree decomposition.
- A method that caches component-level summaries over separator/interface variables.
- A method that invalidates and recomputes only the decomposition region affected by a disruption.
- A method with a soundness theorem under an explicitly stated planning fragment.
- An empirical study comparing local recomputation against full replanning and simpler repair baselines.

### It is not

- A generic “use treewidth for planning” paper.
- A claim that all planning tasks become easy at low treewidth.
- A neural planner, GNN planner, LLM planner, or learned heuristic paper.
- A replacement for full replanning in arbitrary highly coupled tasks.
- A claim of global optimality unless the implementation and theorem genuinely establish it.

### Core novelty claim to preserve

Do not claim that tree decompositions, planning factorization, or decoupled planning are new.

The claim is:

> We formulate execution-time plan repair as localized recomputation of cached, sound interface summaries over a tree decomposition. Under a restricted deterministic planning fragment, only summaries in an affected connected subtree must be recomputed; all unaffected summaries remain reusable, and repair complexity is bounded by the affected subtree structure rather than the full task size.

---

## 3. Research questions

### Main question

Can localized recomputation over a tree decomposition repair plans more efficiently than full replanning when disruptions are local in the planning interaction graph?

### Secondary questions

1. When does local repair remain sound under cached summary reuse?
2. How much does repair speed depend on:
   - the number of affected decomposition bags,
   - separator size,
   - local domain sizes,
   - local transition diversity,
   - disruption radius in the interaction graph?
3. Which planning domains exhibit useful low-interface structure?
4. When is the preprocessing/cache cost amortized over repeated disruptions?
5. How often does the method need to fall back to full replanning?

---

## 4. Formal problem definition

### Planning model

Start with a restricted deterministic finite-domain planning (FDR/SAS+) fragment.

A planning task is:

\[
\Pi = \langle V, D, A, s_0, G, c \rangle
\]

where:

- \(V\) is a finite set of state variables.
- \(D(v)\) is the finite domain of variable \(v\).
- \(A\) is a finite set of deterministic actions.
- \(s_0\) is the initial state.
- \(G\) is a partial goal assignment.
- \(c(a) \ge 0\) is the action cost.

Each action has:

- preconditions \(\mathrm{pre}(a)\),
- effects \(\mathrm{eff}(a)\),
- optional conditional effects only if the selected fragment supports them safely.

### Recommended initial fragment

Implement and prove results first for tasks satisfying all of the following:

1. Deterministic, fully observable state transitions.
2. Finite-domain variables.
3. Nonnegative action costs.
4. No conditional effects in the first theorem version.
5. Each action’s scope is contained in one decomposition bag or can be assigned to one bag with all affected variables present.
6. Cross-bag interactions occur only through separator variables.
7. Goal variables are assigned to bags in a consistent way.
8. The decomposition satisfies the running-intersection property.

Do not broaden the formal fragment until the base theorem and implementation are correct.

### Disruption model

A disruption \(\delta\) is a local modification observed during execution. Initial supported types:

- State fact/variable-value change: \(v := d\).
- Action failure causing expected effects not to occur.
- Temporary action unavailability.
- Resource/capacity variable change, if represented directly in FDR.
- Local edge/action removal from the induced interaction graph.

Represent the post-disruption task/state as \(\Pi^\delta\) and current execution state \(s^\delta\).

### Repair objective

Primary objective for the first implementation:

> Find any valid plan from \(s^\delta\) to \(G\) while maximizing reuse of cached summaries and minimizing repair computation time.

Secondary objectives, added only after validity is stable:

- minimize action cost,
- minimize number of changed actions relative to the original plan,
- minimize makespan,
- minimize recomputed bags,
- minimize deviation from original suffix.

Avoid mixing all objectives in the first paper implementation. Report repair time and plan validity first; cost is a separate column.

---

## 5. Graph representation and decomposition

### Interaction graph

Use a graph over FDR variables. The default is a **primal action-interaction graph**:

- One node per state variable.
- Add an undirected edge between two variables if they appear together in the precondition/effect scope of an action.
- Optionally include goal co-occurrence edges if needed for summary composition.

Maintain a separate directed causal graph for analysis and visualization, but build the tree decomposition over a graph whose bag scopes safely cover action interactions.

### Tree decomposition

A tree decomposition is \(\mathcal{T} = (T, \{B_t\}_{t \in T})\), where:

- \(T\) is a tree.
- Each bag \(B_t \subseteq V\).
- Every variable appears in at least one bag.
- Every interaction edge is contained in at least one bag.
- Bags containing any variable form a connected subtree.

Root the decomposition at an arbitrary bag selected by a heuristic:

- Prefer a bag containing goal variables.
- Break ties by small separator sizes.

### Bag ownership

Assign every action to exactly one bag containing its full scope.

Assignment rule:

1. Find all bags whose scope contains all variables used by the action.
2. Choose the shallowest bag closest to the root.
3. Use a deterministic tie-breaker by bag id.

Never duplicate action ownership unless the proof explicitly permits it.

### Separators

For a non-root bag \(t\) with parent \(p(t)\):

\[
S_t = B_t \cap B_{p(t)}
\]

The separator is the only information that the child summary may expose to the rest of the decomposition.

---

## 6. Interface summary semantics

### Required invariant

Every cached summary must have a precise semantic meaning. Do not store opaque heuristic scores as if they were proof-relevant summaries.

### Core summary type

For bag \(t\), define a summary table:

\[
\Sigma_t(i, o) = \min \{ \mathrm{cost}(\pi_t) \mid \pi_t \text{ transforms interface assignment } i \text{ into } o \text{ while satisfying the local subtree obligations} \}
\]

where:

- \(i\) is an assignment to the separator variables entering the bag/subtree,
- \(o\) is an assignment to the separator variables leaving the bag/subtree,
- \(\pi_t\) is a local plan fragment using actions owned by the subtree rooted at \(t\),
- infeasible transitions have cost \(+\infty\).

For a root bag, the summary maps initial compatible assignments to goal-satisfying assignments.

### Summary payload

Each summary entry should store:

```text
SummaryEntry:
  feasible: bool
  cost: float | int
  local_plan_fragment: optional list[ActionID]
  child_interface_choices: optional mapping[ChildBagID, InterfaceAssignment]
  validity_certificate: optional structured witness
  provenance:
    bag_id
    task_version
    dependency_versions
    computed_at
```

### Soundness requirement

A summary entry may be reused only if:

1. The bag-local actions and variable domains it depends on have not changed.
2. Every child summary dependency remains valid for the same task version.
3. The disruption does not alter a local state/action/resource fact outside the summary’s declared interface assumptions.
4. The entry’s separator assignment remains well-typed and feasible.

If any condition is uncertain, invalidate rather than reuse.

Correctness beats cache hit rate.

---

## 7. Localized recomputation algorithm

### High-level algorithm

```text
INPUT:
  Current task/state Πδ, rooted tree decomposition T,
  cached summaries Σ, disruption δ

1. Determine directly affected variables/actions R0.
2. Map R0 to owning bags B0.
3. Compute the minimal connected affected subtree Tδ containing B0.
4. Expand Tδ if a changed separator value or changed child summary invalidates an ancestor summary.
5. Invalidate summaries for bags in Tδ.
6. Recompute summaries bottom-up only within Tδ.
7. Reuse cached summaries outside Tδ if dependency versions match.
8. Propagate updated interface summaries from the boundary of Tδ toward the root.
9. Compose a repaired plan from root summary witnesses.
10. Validate the final plan with an independent transition simulator/validator.
11. If no valid root summary exists, fall back to full replanning and log the fallback.
```

### Important distinction: direct versus propagated impact

- **Directly affected bags** own changed actions/variables.
- **Affected subtree** includes bags whose summaries become invalid because their interfaces or descendant summaries changed.

The implementation must track both. A disruption can be local, while its summary consequences propagate toward the root through separators.

### Conservative impact policy

For the first correct implementation:

- Mark all bags containing a changed variable.
- Mark the Steiner tree connecting them.
- Mark every ancestor to the root whose summary depends on an updated child interface.
- Recompute only the marked bags.

This may recompute more than minimally necessary, but it is easier to make sound.

Optimize invalidation only after correctness tests pass.

---

## 8. The theorem target

### Main theorem — sound localized repair

Prove a theorem in this shape.

> **Theorem (Sound Localized Recomputation).**
> Let \(\Pi\) be a deterministic finite-domain planning task in the supported fragment, and let \(\mathcal{T}\) be a rooted tree decomposition satisfying action-scope coverage and running intersection. Let \(\Sigma\) be a collection of sound cached interface summaries for \(\Pi\). After a local disruption \(\delta\), let \(T_\delta\) be a connected affected subtree containing every bag whose locally owned actions, domains, state assumptions, or descendant summaries are invalidated by \(\delta\). If summaries are recomputed bottom-up for all bags in \(T_\delta\), all summaries outside \(T_\delta\) remain valid under their declared interface assumptions, and the recomposed root summary contains a feasible witness, then the extracted repaired plan is executable from \(s^\delta\) and reaches \(G\).

### Complexity theorem — affected-subtree bound

Prove a bound in this shape.

Define:

- \(n_\delta = |T_\delta|\): number of recomputed bags.
- \(w_\delta = \max_{t \in T_\delta} |B_t| - 1\): affected subtree treewidth.
- \(s_\delta = \max_{t \in T_\delta} |S_t|\): largest affected separator size.
- \(d = \max_{v \in V}|D(v)|\): maximum variable domain size.
- \(m_\delta\): number of locally owned actions in the affected subtree.
- \(\tau_t\): cost of the local summary solver for bag \(t\).

Target bound:

\[
T_{\mathrm{repair}}
\in
O\left(
\sum_{t \in T_\delta} \tau_t
+
|T_\delta| \cdot d^{O(s_\delta)}
\right)
\]

and, for an enumerative local solver over bags:

\[
T_{\mathrm{repair}}
\in
O\left(
|T_\delta| \cdot \mathrm{poly}(m_\delta) \cdot d^{O(w_\delta + 1)}
\right).
\]

The theorem should explicitly contrast this with a full recomputation bound depending on full-tree size \(|T|\) and global width \(w\):

\[
T_{\mathrm{full}}
\in
O\left(
|T| \cdot \mathrm{poly}(m) \cdot d^{O(w + 1)}
\right).
\]

### Do not overclaim

The bound does **not** imply that repair is always fast.

State clearly:

- Worst-case planning remains hard.
- If the disruption affects a large subtree or interfaces are large, the advantage may vanish.
- The decomposition preprocessing and summary construction can be expensive.
- The result is a parameterized/locality-sensitive bound, not a universal polynomial-time guarantee.

### Proof structure

Organize the proof around four lemmas:

1. **Bag-locality lemma:** every owned action and its relevant variables are represented in its owner bag.
2. **Separator sufficiency lemma:** information needed by a child subtree to interact with the remainder is captured by its separator assignment.
3. **Summary composition lemma:** compatible sound child summaries and local actions compose into a sound parent summary.
4. **Unaffected-summary reuse lemma:** summaries outside the affected subtree remain sound because all of their local dependencies and interface assumptions remain unchanged.

Then prove the main theorem by induction from leaves of \(T_\delta\) to the root / affected boundary.

---

## 9. Implementation architecture

### Required modules

```text
src/
  fdr/
    parser.py                 # SAS+/FDR task loader
    task.py                   # Variables, actions, states, goals
    simulator.py              # Deterministic plan execution and validation

  graph/
    interaction_graph.py      # Variable/action interaction graph
    causal_graph.py           # Directed causal graph for diagnostics
    decomposition.py          # Tree decomposition adapters and normalization
    bag_assignment.py         # Action ownership and separator construction

  summaries/
    interface.py              # InterfaceAssignment, SummaryEntry, SummaryTable
    local_solver.py           # Exact local summary computation
    compose.py                # Bottom-up parent summary composition
    cache.py                  # Versioned cache and dependency tracking
    invalidation.py           # Affected-bag/subtree computation

  repair/
    disruption.py             # Disruption data model and injection
    localized_repair.py       # Main algorithm
    full_replan.py            # Baseline wrapper
    suffix_reuse.py           # Baseline wrapper
    fixed_window.py           # Baseline wrapper

  experiments/
    generators/               # Synthetic loosely coupled task generators
    runners/                  # Benchmark task runners
    metrics.py                # Runtime, expansions, reuse, validity metrics
    plotting.py               # Paper-ready plots

  tests/
    unit/
    property/
    integration/
    regression/
```

### Recommended language and stack

- Python 3.11+ for orchestration and experiments.
- Existing planner binaries for baseline full replanning, initially Fast Downward.
- `networkx` only for prototypes/diagnostics; avoid it in inner loops if it becomes slow.
- A tree-decomposition package or external solver for initial decomposition construction.
- `pytest` for tests.
- `pydantic` or dataclasses for immutable task/summary records.
- `numpy` for compact tables if needed.
- CSV/Parquet/JSONL for experiment logs.

### Performance rule

The correctness path must work in pure Python first. Optimize only after profiling.

Do not write C++ or Rust until:

1. the theorem assumptions are encoded,
2. unit tests pass,
3. a small benchmark demonstrates the expected scaling trend,
4. profiling identifies a real bottleneck.

---

## 10. Summary computation strategy

### Phase 1: exact, small-scale summaries

Start with a restricted local solver that enumerates local states and interface assignments for small bags.

For each bag/subtree:

1. Enumerate reachable local configurations consistent with each input separator assignment.
2. Compose child summaries through compatible interface assignments.
3. Record cheapest or first-found local witness for each output separator assignment.

This is not intended to scale immediately. It establishes semantic correctness.

### Phase 2: structured local solver

Replace brute-force local enumeration with one of:

- local Dijkstra / uniform-cost search,
- local BFS for unit costs,
- SAT/PB bounded local planning,
- symbolic BDD-based transition summaries,
- partial-order local plan construction.

Choose one and document its assumptions. Do not combine several sophisticated solvers in version one.

### Phase 3: selective materialization

Avoid computing every possible interface pair when unnecessary.

Possible safe optimizations:

- lazy summary entries keyed by observed interface assignments,
- dominance pruning for cost vectors,
- compact signature hashing,
- memoized local reachability,
- bounded cache size with explicit invalidation.

Never sacrifice summary soundness for cache compression.

---

## 11. Baselines

### Mandatory baselines

1. **Full replanning:** solve from the post-disruption state with the same planner/heuristic.
2. **Original-plan suffix reuse:** keep the longest valid suffix when possible; replan otherwise.
3. **Fixed-window repair:** replan a fixed local window around the failure.
4. **No-cache decomposition:** use the same decomposition but recompute all summaries after every disruption.
5. **Localized recomputation (ours):** recompute only the affected subtree.

### Stronger baseline when feasible

6. **Existing decoupled/factored planning method:** only if a runnable implementation is available and the comparison is fair.

### Fairness rules

- Use identical domain/problem instances and disruption seeds.
- Give all methods the same wall-clock timeout.
- Report preprocessing separately from online repair time.
- Report cache memory separately from runtime.
- Do not count an invalid repaired plan as a success.
- Validate every plan independently.

---

## 12. Experimental plan

### Experiment A — proof of locality on synthetic tasks

Build a synthetic generator for loosely coupled planning tasks with:

- \(k\) local regions,
- one or more small shared separators,
- controllable bag width,
- controllable affected-subtree size,
- controllable disruption location and magnitude.

Examples:

- multi-zone logistics with a shared hub,
- factory cells with shared transfer buffers,
- corridor/room navigation with limited doorway variables,
- modular transport with one shared vehicle/charger variable.

Primary sweep:

- number of regions,
- separator size,
- affected subtree fraction,
- disruption radius,
- number of repeated disruptions.

Expected finding:

> Online repair time tracks the affected subtree size and separator width much more closely than the full problem size.

### Experiment B — repeated-disruption amortization

For each base instance:

1. Solve once and build/cache summaries.
2. Inject a sequence of local disruptions.
3. Repair after each disruption.
4. Compare cumulative time against repeated full replanning.

Report:

- initial preprocessing cost,
- total repair cost over \(r\) disruptions,
- break-even number of disruptions,
- cache hit rate,
- average affected subtree size.

### Experiment C — standard planning domains

Start with domains that may have modular/logistics structure:

- Logistics,
- Transport,
- Driverlog,
- Rovers,
- Satellite,
- Depot,
- Elevators if available.

Use controlled disruptions:

- action failure,
- road/route fact changes,
- object availability changes,
- capacity changes,
- temporary resource/action unavailability.

Do not claim every IPC domain has favorable decomposition structure. Stratify results by measured structural properties.

### Experiment D — negative cases

Include highly coupled or dense-interaction instances.

Show honestly that:

- decompositions have large bags/separators,
- cache construction can be costly,
- local recomputation advantage can disappear,
- fallback to full replanning may be appropriate.

A credible negative result makes the contribution stronger.

---

## 13. Metrics

### Validity and solution quality

- Repair success rate.
- Independent plan validation pass rate.
- Repaired plan cost.
- Repaired plan length.
- Relative cost difference from full replanning.
- Number/percentage of actions reused from original plan, when a reference plan exists.

### Runtime and search effort

- Online repair wall-clock time.
- Total time including preprocessing.
- Number of recomputed bags.
- Fraction of decomposition bags reused.
- Number of local state expansions.
- Number of global planner expansions for full-replan baseline.
- Cache hits, misses, invalidations.
- Peak memory and cache size.

### Structural predictors

- Global treewidth estimate.
- Affected-subtree width \(w_\delta\).
- Maximum affected separator size \(s_\delta\).
- Affected bag count \(n_\delta\).
- Fraction of graph variables/actions directly affected.
- Interface transition table density.

### Essential plots

1. Repair time vs. affected-subtree size.
2. Repair time vs. maximum affected separator size.
3. Cumulative time vs. number of disruptions.
4. Cache hit rate vs. disruption locality.
5. Full replan vs. no-cache factorization vs. localized repair.
6. Scatter: predicted structural parameter vs. measured repair time.

---

## 14. Reproducibility requirements

Every experiment run must record:

```json
{
  "git_commit": "...",
  "instance_id": "...",
  "domain": "...",
  "seed": 0,
  "disruption_id": "...",
  "disruption_type": "...",
  "decomposition_method": "...",
  "global_treewidth_estimate": 0,
  "affected_bag_count": 0,
  "affected_separator_max": 0,
  "method": "...",
  "timeout_seconds": 0,
  "success": true,
  "plan_valid": true,
  "preprocess_seconds": 0.0,
  "repair_seconds": 0.0,
  "total_seconds": 0.0,
  "cache_hits": 0,
  "cache_misses": 0,
  "peak_memory_mb": 0.0
}
```

Requirements:

- Fix and log random seeds.
- Keep raw run logs, not only aggregated tables.
- Separate preprocessing from online repair time.
- Publish instance-generation scripts.
- Use a deterministic action-ordering policy where possible.
- Validate all output plans with an independent simulator.
- Preserve failed runs and timeouts in result tables.

---

## 15. Testing strategy

### Unit tests

Test independently:

- FDR state transition semantics.
- Action applicability and effects.
- Interaction graph construction.
- Tree decomposition validity.
- Action ownership: every action assigned once; owner bag covers its scope.
- Separator construction.
- Summary entry serialization and version checking.
- Invalidation propagation.
- Summary composition.

### Property-based tests

Generate small random planning tasks within the supported fragment and assert:

1. Full recomputation and localized recomputation agree on feasibility.
2. If both return plans, both plans validate.
3. Reused summaries are never reused after a declared dependency changes.
4. A local disruption with no path to a bag’s dependencies does not invalidate that bag.
5. Cache invalidation is conservative: false positives are allowed; false negatives are not.

### Differential tests

For tiny instances where exhaustive global search is feasible:

- Compare local-summary composition against exhaustive shortest-path planning.
- Compare repaired plan cost against the exact global optimum if optimizing cost.
- Compare post-disruption reachability against a reference BFS/Dijkstra solver.

### Regression tests

Every bug involving an invalid plan, stale summary, or incorrect invalidation must become a minimized regression case.

---

## 16. Coding standards for Claude

### Correctness before cleverness

- Keep the initial implementation simple and inspectable.
- Prefer explicit data structures over implicit global state.
- Add assertions at all decomposition and summary boundaries.
- Do not optimize away validation.
- Use immutable task versions and cache dependency fingerprints.

### Avoid unsafe shortcuts

Do not:

- reuse a summary after an action, variable domain, state assumption, or child dependency changes without proof of safety;
- assume a causal graph edge alone establishes safe factorization;
- merge bag summaries based on matching variable names without checking assignments;
- report a plan as repaired without simulating it from the actual disrupted state;
- silently fall back to full replanning without logging it.

### Logging

Every repair run should explain:

```text
- Directly changed variables/actions
- Directly affected bags
- Final affected subtree
- Reused bags
- Recomputed bags
- Boundary separators
- Whether root summary was feasible
- Whether fallback occurred
- Final plan validation result
```

### Naming

Use these terms consistently:

- `bag`: one node in the tree decomposition.
- `separator`: parent-child variable intersection.
- `summary`: a sound interface transition table/witness.
- `affected subtree`: bags invalidated by the disruption or propagation.
- `local solver`: method computing one bag/subtree summary.
- `full replan`: solve global post-disruption task without cache reuse.
- `repair`: any valid plan from the post-disruption state to the goal.

Do not use “module,” “cluster,” “component,” and “bag” interchangeably.

---

## 17. Milestones

### Milestone 0 — literature and formal scope

Deliverables:

- One-page related-work map.
- Exact supported planning fragment.
- Draft theorem statement and proof outline.
- Decision on interaction graph and decomposition package.

Exit criterion:

A reviewer can understand what is new compared with static factored planning.

### Milestone 1 — tiny correct prototype

Deliverables:

- Hand-authored small FDR tasks.
- Valid tree decompositions.
- Exact summaries by enumeration.
- Localized invalidation.
- Plan extraction and independent validation.

Exit criterion:

Localized repair and full recomputation match feasibility on all tiny exhaustive tests.

### Milestone 2 — synthetic locality benchmark

Deliverables:

- Generator with tunable regions, separator size, and disruption locality.
- Plots demonstrating repair-time scaling with affected subtree size.

Exit criterion:

At least one clear regime where localized recomputation beats full recomputation after amortizing cache construction over repeated disruptions.

### Milestone 3 — standard domain integration

Deliverables:

- SAS+/PDDL conversion pipeline.
- Full-replanning baseline via existing planner.
- At least three IPC-style domains.
- Disruption injector.

Exit criterion:

Valid repairs and reproducible result tables across multiple seeds/instances.

### Milestone 4 — theory and ablations

Deliverables:

- Complete proof for restricted fragment.
- Complexity theorem.
- Ablations: no cache, all-bag recomputation, different decompositions, disruption locality.

Exit criterion:

The paper’s main claim survives ablations and negative-case analysis.

### Milestone 5 — paper package

Deliverables:

- Reproducible scripts.
- Artifact README.
- Figure generation from raw logs.
- Draft paper with limitations section.

---

## 18. Paper narrative

### Problem

Real planning systems face repeated local disruptions. Full replanning discards useful computation even when most of the task is unchanged.

### Insight

A tree decomposition exposes small interfaces between loosely coupled planning regions. If component behavior is summarized soundly over those interfaces, then unchanged components need not be solved again.

### Method

Cache interface summaries, detect the affected subtree after a disruption, recompute only that subtree, and compose reused + updated summaries into a repaired plan.

### Theory

Under a defined planning fragment, repaired plans are sound and online recomputation is bounded by affected-subtree width/size and local solver complexity.

### Evidence

Synthetic tasks establish the locality mechanism; repeated-disruption studies establish amortization; IPC-style domains test practical relevance; negative cases delimit applicability.

### Honest limitations

- Performance depends on exploitable low-interface structure.
- Decomposition quality matters.
- Summary tables may grow exponentially in separator size.
- Strongly coupled tasks may require full replanning.
- The first theorem applies only to a restricted deterministic planning fragment.

---

## 19. Suggested command interface

```bash
# Validate a decomposition for one task
python -m src.cli decompose \
  --task data/tasks/example.sas \
  --method min_fill \
  --validate

# Build summaries and solve initial task
python -m src.cli solve \
  --task data/tasks/example.sas \
  --decomposition artifacts/example_decomp.json \
  --cache-dir artifacts/cache/example

# Inject one disruption and repair locally
python -m src.cli repair \
  --task data/tasks/example.sas \
  --cache-dir artifacts/cache/example \
  --disruption configs/disruptions/blocked_route_01.json \
  --method localized

# Compare all baselines on a benchmark suite
python -m src.cli benchmark \
  --suite configs/suites/logistics_local_failures.yaml \
  --methods full_replan,suffix_reuse,fixed_window,no_cache,localized \
  --seeds 0,1,2,3,4 \
  --out results/logistics_local_failures

# Recreate figures from raw logs
python -m src.cli plot \
  --results results/logistics_local_failures \
  --out figures/
```

The exact command names can change, but preserve the separation between decomposition, cache construction, repair, benchmarking, and plotting.

---

## 20. Decision rules for future extensions

Only add an extension if it strengthens the main claim.

### Good extensions

- Better affected-subtree detection with the same soundness invariant.
- Lazy summary materialization.
- Alternative decomposition heuristics.
- Multi-objective repair cost once validity is established.
- Incremental cache maintenance across many disruptions.
- A stronger structural predictor than raw treewidth.

### Do not add early

- Learned GNN decomposition selection.
- LLM-generated repair plans.
- Multi-agent planning unless the base algorithm already works.
- Temporal planning, stochastic planning, conditional effects, or numeric fluents.
- A complex web UI.
- Unrelated benchmark breadth.

The paper wins by making one locality-sensitive algorithm and theorem convincing—not by accumulating features.

---

## 21. Definition of done for the first publishable version

The project is ready to write up when all are true:

1. A formal supported fragment is stated precisely.
2. The localized-recomputation theorem is proven for that fragment.
3. Summary reuse is independently validated by tests.
4. Synthetic experiments show a clear advantage when disruptions are local.
5. The method is compared against full replanning and no-cache recomputation fairly.
6. At least three recognizable planning domains are evaluated.
7. Negative/high-coupling cases are reported honestly.
8. Runtime, memory, preprocessing, cache size, and fallbacks are all reported.
9. All output plans are independently validated.
10. The code and benchmark generation are reproducible from a clean environment.

---

## 22. Final instruction to the coding assistant

When implementing or modifying this project:

1. Preserve summary semantics and soundness invariants first.
2. Prefer a smaller correct theorem fragment over a broad vague claim.
3. Treat stale-summary reuse as a correctness bug, not a performance optimization.
4. Keep experiments focused on showing locality-sensitive repair, not generic planner superiority.
5. Always separate offline preprocessing time from online repair time.
6. Always validate reconstructed plans independently.
7. When an assumption is needed, document it explicitly in code and in the paper notes.
8. When a result is negative, log and report it; it helps define applicability.

The central standard is:

> Every claimed speedup must be traceable to a valid reuse of unchanged decomposition summaries, and every returned repair must be executable from the disrupted state.
