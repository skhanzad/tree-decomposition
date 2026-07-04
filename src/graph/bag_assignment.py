from __future__ import annotations

from typing import Dict, List, Tuple

from src.fdr.task import Action, Task
from src.graph.decomposition import TreeDecomposition


def assign_actions(task: Task, decomposition: TreeDecomposition) -> Dict[str, Tuple[Action, ...]]:
    assignment: Dict[str, List[Action]] = {bag_id: [] for bag_id in decomposition.bags}
    depth = _bag_depths(decomposition)

    for action in task.actions:
        covering = [bag_id for bag_id, bag in decomposition.bags.items() if action.scope <= bag.variables]
        if not covering:
            raise ValueError(f"action {action.name!r} has no covering bag for scope {sorted(action.scope)}")
        chosen = min(covering, key=lambda bag_id: (depth[bag_id], bag_id))
        assignment[chosen].append(action)

    return {bag_id: tuple(sorted(actions, key=lambda a: a.name)) for bag_id, actions in assignment.items()}


def _bag_depths(decomposition: TreeDecomposition) -> Dict[str, int]:
    depths: Dict[str, int] = {decomposition.root_id: 0}
    stack = [decomposition.root_id]
    while stack:
        current = stack.pop()
        for child_id in decomposition.children_of(current):
            depths[child_id] = depths[current] + 1
            stack.append(child_id)
    return depths
