# Draft Theorem Statement and Proof Outline

Status: draft for Milestone 0 / Milestone 4 completion  
Fragment: see [supported-fragment.md](./supported-fragment.md)

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| \(\Pi, \mathcal{T}, \Sigma\) | Task, rooted tree decomposition, cached summary collection |
| \(\delta\) | Local disruption; post-disruption task/state \((\Pi^\delta, s^\delta)\) |
| \(T_\delta \subseteq T\) | Connected **affected subtree** (invalidated bags + ancestors) |
| \(S_t\) | Separator \(B_t \cap B_{p(t)}\) for non-root \(t\) |
| \(\Sigma_t(i,o)\) | Minimum-cost local transition from incoming interface \(i\) to outgoing \(o\) at bag \(t\) |
| \(n_\delta = \|T_\delta\|\) | Number of bags recomputed |
| \(w_\delta = \max_{t \in T_\delta} (\|B_t\|-1)\) | Max bag width in affected subtree |
| \(s_\delta = \max_{t \in T_\delta} \|S_t\|\) | Max separator size in affected subtree |
| \(d = \max_{v \in V} \|D(v)\|\) | Max domain size |
| \(m_\delta\) | Actions owned in affected subtree |

A summary entry is **sound** for task version \(\nu\) if its stored cost and witness plan fragment are correct for the declared local actions, state assumptions, child dependencies, and interface assignments.

---

## Theorem 1 — Sound localized recomputation

> **Theorem (Sound Localized Recomputation).**  
> Let \(\Pi\) be a deterministic finite-domain planning task satisfying assumptions A1–A8. Let \(\mathcal{T}\) be a rooted tree decomposition with deterministic action ownership and running intersection. Let \(\Sigma\) be a collection of sound cached interface summaries for task version \(\nu\).  
> After disruption \(\delta\), let \(T_\delta\) be a connected affected subtree that contains every bag whose locally owned actions, domains, state assumptions, or descendant summaries are invalidated by \(\delta\), and all ancestors required for separator propagation.  
> Suppose summaries are invalidated on \(T_\delta\) and recomputed bottom-up on \(T_\delta\) only, while summaries outside \(T_\delta\) are reused unchanged. If the recomposed root summary contains a feasible witness, then the extracted repaired plan is executable from \(s^\delta\) and satisfies \(G\).

### Proof outline

Induction on a postorder of bags in \(T_\delta\), using four lemmas:

#### Lemma 1 — Bag locality

Every action owned by bag \(t\) has \(\mathrm{scope}(a) \subseteq B_t\), and all variables needed to apply that action inside the subtree appear in the bag-local state construction.

*Proof sketch:* From ownership rule A5 and decomposition coverage of interaction edges.

#### Lemma 2 — Separator sufficiency

For child bag \(c\) with parent \(p\), any behavior of the subtree rooted at \(c\) that is relevant to the rest of the tree is fully determined by the assignment to \(S_c = B_c \cap B_p\).

*Proof sketch:* Running intersection (A4) ensures no interaction bypasses shared separators; cross-bag coupling is only through separator variables (A6).

#### Lemma 3 — Summary composition

If child summaries on \(T_\delta\) are sound and bag-local actions are unchanged outside their invalidation, then bottom-up composition at parent bag \(t\) yields sound \(\Sigma_t\) for the updated task version.

*Proof sketch:* Standard dynamic programming on a junction tree: combine minimum-cost local fragments consistent on shared interfaces; root additionally enforces goal (A7).

#### Lemma 4 — Unaffected-summary reuse

For any bag \(t \notin T_\delta\), if \(\Sigma_t\) was sound before \(\delta\) and no dependency in its fingerprint changed, then \(\Sigma_t\) remains sound for \(\Pi^\delta\) under the same interface assumptions.

*Proof sketch:* \(\delta\) does not alter actions owned in the subtree of \(t\), nor state facts outside declared interfaces, nor child summaries that remain cached; conservative \(T_\delta\) only excludes bags where a dependency might have changed.

#### Main induction

- **Base (leaves of \(T_\delta\)):** Recompute leaf summaries with exact local solver; sound by construction given sound child caches (outside subtree) and Lemma 1–2.
- **Step (internal bag \(t \in T_\delta\)):** Sound child summaries on affected children plus reused sound children outside give sound inputs; apply Lemma 3.
- **Root:** Feasible root witness yields a composed plan; simulator validation is independent check (implementation requirement).

**Fallback:** If root summary is infeasible, algorithm may call full replan; theorem applies to the **localized path** when root summary is feasible.

---

## Theorem 2 — Affected-subtree repair complexity

> **Theorem (Repair complexity bound — draft).**  
> Under the same assumptions, let \(\tau_t\) be the time to compute the summary table at bag \(t\) with the chosen local solver. Localized repair time satisfies
> \[
> T_{\mathrm{repair}} \in O\!\left(\sum_{t \in T_\delta} \tau_t + |T_\delta| \cdot d^{O(s_\delta)}\right).
> \]
> For the enumerative Phase-1 local solver (M1), \(\tau_t \in O(\mathrm{poly}(m_t) \cdot d^{O(w_\delta+1)})\), hence
> \[
> T_{\mathrm{repair}} \in O\!\left(|T_\delta| \cdot \mathrm{poly}(m_\delta) \cdot d^{O(w_\delta+1)}\right).
> \]

### Contrast with full recomputation

Full replanning / recomputing all summaries satisfies

\[
T_{\mathrm{full}} \in O\!\left(|T| \cdot \mathrm{poly}(m) \cdot d^{O(w+1)}\right)
\]

where \(|T|\) is total bag count and \(w\) is global width.

**Interpretation:** Advantage appears when \(|T_\delta| \ll |T|\) and \(s_\delta, w_\delta\) stay small. **Not** a universal polynomial-time planning result.

### Proof sketch

- Only bags in \(T_\delta\) invoke \(\tau_t\); reuse is \(O(1)\) lookup per unaffected bag.
- Interface tables have at most \(d^{|S_t|}\) assignments per separator; \(|S_t| \le s_\delta\).
- Enumerative local solver explores bag-local state space bounded by \(d^{|B_t|}\) with \(|B_t|-1 \le w_\delta\).

---

## Limitations paragraph (for paper)

- Preprocessing to build initial \(\Sigma\) can dominate first repair.
- Decomposition quality is instance-dependent; negative cases (large \(w\), large \(T_\delta\)) are expected.
- Separator tables grow exponentially in \(|S_t|\); lazy materialization is future work.
- v1 fragment excludes conditional effects and many disruption types.

---

## Milestone 4 completion criteria for proofs

- [ ] Formalize Lemma 1–4 in appendix with explicit notation matching code
- [ ] State fingerprint / version conditions matching `compute_fingerprint`
- [ ] Connect conservative invalidation to \(T_\delta\) definition
- [ ] Separate corollary for cost-optimality under exact summaries (optional)
