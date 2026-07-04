from __future__ import annotations

from typing import Dict, List, Tuple

from src.fdr.task import Action, State, Task
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import TreeDecomposition
from src.summaries.interface import ChildJumpStep, OwnActionStep, SummaryEntry, SummaryTable
from src.summaries.local_solver import solve_bag


def compute_all_summaries(
    task: Task,
    decomposition: TreeDecomposition,
    current_state: State,
    task_version: str,
) -> Dict[str, SummaryTable]:
    owned = assign_actions(task, decomposition)
    tables: Dict[str, SummaryTable] = {}

    for bag_id in decomposition.postorder():
        child_tables = {cid: tables[cid] for cid in decomposition.children_of(bag_id)}
        goal = task.goal if bag_id == decomposition.root_id else None
        tables[bag_id] = solve_bag(
            decomposition=decomposition,
            bag_id=bag_id,
            owned_actions=owned[bag_id],
            current_state=current_state,
            child_tables=child_tables,
            task_version=task_version,
            variables=task.variables,
            goal=goal,
        )

    return tables


def extract_plan(tables: Dict[str, SummaryTable], root_entry: SummaryEntry) -> Tuple[Action, ...]:
    actions: List[Action] = []

    def expand(entry: SummaryEntry) -> None:
        for step in entry.local_plan_fragment:
            if isinstance(step, OwnActionStep):
                actions.append(step.action)
            elif isinstance(step, ChildJumpStep):
                child_entry = tables[step.child_bag_id].get(step.incoming, step.outgoing)
                if child_entry is None or not child_entry.feasible:
                    raise ValueError(f"missing or infeasible child entry for bag {step.child_bag_id!r}")
                expand(child_entry)

    expand(root_entry)
    return tuple(actions)
