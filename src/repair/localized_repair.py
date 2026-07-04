from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional, Tuple

from src.fdr.simulator import validate_plan
from src.fdr.task import Action, State, Task
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import TreeDecomposition
from src.repair.disruption import Disruption, affected_action_names, affected_variables, apply_disruption
from src.repair.full_replan import full_replan
from src.summaries.cache import SummaryCache, compute_fingerprint
from src.summaries.compose import extract_plan
from src.summaries.interface import SummaryTable
from src.summaries.invalidation import directly_affected_bags, expand_to_affected_subtree
from src.summaries.local_solver import solve_bag


@dataclass(frozen=True)
class RepairLog:
    directly_changed_variables: FrozenSet[str]
    directly_changed_actions: FrozenSet[str]
    directly_affected_bags: FrozenSet[str]
    affected_subtree: FrozenSet[str]
    reused_bags: FrozenSet[str]
    recomputed_bags: FrozenSet[str]
    root_feasible: bool
    fallback_occurred: bool
    plan_valid: Optional[bool]


@dataclass(frozen=True)
class RepairResult:
    plan: Optional[Tuple[Action, ...]]
    cost: Optional[float]
    log: RepairLog


def repair(
    task: Task,
    decomposition: TreeDecomposition,
    state: State,
    disruption: Disruption,
    cache: SummaryCache,
    task_version: str,
) -> RepairResult:
    new_task, new_state = apply_disruption(task, state, disruption)
    owned = assign_actions(new_task, decomposition)

    directly_affected = directly_affected_bags(decomposition, owned, disruption)
    affected_subtree = expand_to_affected_subtree(decomposition, directly_affected)
    for bag_id in affected_subtree:
        cache.invalidate(bag_id)

    tables: Dict[str, SummaryTable] = {}
    fingerprints: Dict[str, str] = {}
    reused: set = set()
    recomputed: set = set()

    for bag_id in decomposition.postorder():
        child_fps = tuple(fingerprints[cid] for cid in decomposition.children_of(bag_id))
        fingerprint = compute_fingerprint(decomposition, bag_id, new_state, owned[bag_id], child_fps)
        fingerprints[bag_id] = fingerprint

        cached = cache.get(bag_id, fingerprint)
        if cached is not None:
            tables[bag_id] = cached
            reused.add(bag_id)
            continue

        child_tables = {cid: tables[cid] for cid in decomposition.children_of(bag_id)}
        goal = new_task.goal if bag_id == decomposition.root_id else None
        table = solve_bag(
            decomposition=decomposition,
            bag_id=bag_id,
            owned_actions=owned[bag_id],
            current_state=new_state,
            child_tables=child_tables,
            task_version=task_version,
            variables=new_task.variables,
            goal=goal,
        )
        tables[bag_id] = table
        cache.put(bag_id, fingerprint, table)
        recomputed.add(bag_id)

    root_entry = tables[decomposition.root_id].get((), ())
    root_feasible = root_entry is not None and root_entry.feasible

    fallback_occurred = False
    plan: Optional[Tuple[Action, ...]] = None
    cost: Optional[float] = None
    plan_valid: Optional[bool] = None

    if root_feasible:
        assert root_entry is not None
        plan = extract_plan(tables, root_entry)
        cost = root_entry.cost
        plan_valid = validate_plan(new_task, plan, start=new_state)
    else:
        fallback_occurred = True
        plan = full_replan(new_task, start=new_state)
        if plan is not None:
            cost = float(sum(a.cost for a in plan))
            plan_valid = validate_plan(new_task, plan, start=new_state)

    log = RepairLog(
        directly_changed_variables=affected_variables(disruption),
        directly_changed_actions=affected_action_names(disruption),
        directly_affected_bags=directly_affected,
        affected_subtree=affected_subtree,
        reused_bags=frozenset(reused),
        recomputed_bags=frozenset(recomputed),
        root_feasible=root_feasible,
        fallback_occurred=fallback_occurred,
        plan_valid=plan_valid,
    )
    return RepairResult(plan=plan, cost=cost, log=log)
