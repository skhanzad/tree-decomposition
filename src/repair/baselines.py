from __future__ import annotations

from src.fdr.task import Task
from src.graph.decomposition import TreeDecomposition
from src.repair.disruption import Disruption
from src.repair.full_replan import full_replan
from src.repair.localized_repair import RepairResult, repair
from src.summaries.cache import SummaryCache


def repair_no_cache(
    task: Task,
    decomposition: TreeDecomposition,
    state,
    disruption: Disruption,
    cache: SummaryCache,
    task_version: str,
) -> RepairResult:
    """Baseline: invalidate every bag before localized recomputation."""
    for bag_id in decomposition.bags:
        cache.invalidate(bag_id)
    return repair(task, decomposition, state, disruption, cache, task_version)


def repair_full_replan(
    task: Task,
    state,
    disruption: Disruption,
) -> RepairResult:
    """Baseline: ignore decomposition cache entirely."""
    from src.repair.disruption import apply_disruption, affected_action_names, affected_variables
    from src.fdr.simulator import validate_plan

    new_task, new_state = apply_disruption(task, state, disruption)
    plan = full_replan(new_task, start=new_state)
    from src.repair.localized_repair import RepairLog

    empty = frozenset()
    if plan is None:
        log = RepairLog(
            directly_changed_variables=affected_variables(disruption),
            directly_changed_actions=affected_action_names(disruption),
            directly_affected_bags=empty,
            affected_subtree=empty,
            reused_bags=empty,
            recomputed_bags=empty,
            root_feasible=False,
            fallback_occurred=False,
            plan_valid=False,
        )
        return RepairResult(plan=None, cost=None, log=log)

    cost = float(sum(a.cost for a in plan))
    valid = validate_plan(new_task, plan, start=new_state)
    log = RepairLog(
        directly_changed_variables=affected_variables(disruption),
        directly_changed_actions=affected_action_names(disruption),
        directly_affected_bags=empty,
        affected_subtree=empty,
        reused_bags=empty,
        recomputed_bags=empty,
        root_feasible=True,
        fallback_occurred=False,
        plan_valid=valid,
    )
    return RepairResult(plan=plan, cost=cost, log=log)
