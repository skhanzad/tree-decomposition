from __future__ import annotations

from typing import Dict, FrozenSet, Set, Tuple

from src.fdr.task import Action
from src.graph.decomposition import TreeDecomposition
from src.repair.disruption import Disruption, affected_action_names, affected_variables


def directly_affected_bags(
    decomposition: TreeDecomposition,
    owned: Dict[str, Tuple[Action, ...]],
    disruption: Disruption,
) -> FrozenSet[str]:
    changed_vars = affected_variables(disruption)
    changed_action_names = affected_action_names(disruption)
    affected: Set[str] = set()

    for bag_id, bag in decomposition.bags.items():
        if changed_vars & bag.variables:
            affected.add(bag_id)
        if any(action.name in changed_action_names for action in owned.get(bag_id, ())):
            affected.add(bag_id)

    return frozenset(affected)


def expand_to_affected_subtree(decomposition: TreeDecomposition, directly_affected: FrozenSet[str]) -> FrozenSet[str]:
    affected: Set[str] = set(directly_affected)
    for bag_id in directly_affected:
        current = bag_id
        while decomposition.bags[current].parent_id is not None:
            current = decomposition.bags[current].parent_id
            affected.add(current)
    return frozenset(affected)
