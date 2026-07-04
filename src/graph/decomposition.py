from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

import networkx as nx
from networkx.algorithms.approximation.treewidth import treewidth_min_fill_in

from src.fdr.task import Task


@dataclass(frozen=True)
class Bag:
    bag_id: str
    variables: FrozenSet[str]
    parent_id: Optional[str]
    children_ids: Tuple[str, ...]


@dataclass(frozen=True)
class TreeDecomposition:
    bags: Dict[str, Bag]
    root_id: str

    def bag(self, bag_id: str) -> Bag:
        return self.bags[bag_id]

    def separator_to_parent(self, bag_id: str) -> FrozenSet[str]:
        bag = self.bags[bag_id]
        if bag.parent_id is None:
            return frozenset()
        return bag.variables & self.bags[bag.parent_id].variables

    def separator_to_child(self, bag_id: str, child_id: str) -> FrozenSet[str]:
        return self.bags[bag_id].variables & self.bags[child_id].variables

    def children_of(self, bag_id: str) -> Tuple[str, ...]:
        return self.bags[bag_id].children_ids

    def postorder(self) -> Tuple[str, ...]:
        order: List[str] = []

        def visit(bag_id: str) -> None:
            for child_id in self.bags[bag_id].children_ids:
                visit(child_id)
            order.append(bag_id)

        visit(self.root_id)
        return tuple(order)

    def find_bag(self, variables: FrozenSet[str]) -> str:
        matches = [bag_id for bag_id, bag in self.bags.items() if bag.variables == variables]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one bag with variables {variables}, found {len(matches)}")
        return matches[0]


def build_decomposition(task: Task, interaction_graph: nx.Graph) -> TreeDecomposition:
    _, raw_tree = treewidth_min_fill_in(interaction_graph)
    goal_vars = frozenset(var for var, _ in task.goal)

    candidates = [node for node in raw_tree.nodes() if goal_vars <= node]
    if not candidates:
        raise ValueError("no bag contains all goal variables (goal-in-one-bag assumption violated)")
    root_node = min(candidates, key=lambda node: (len(node), sorted(node)))

    bag_ids: Dict[FrozenSet[str], str] = {
        node: f"bag_{i}" for i, node in enumerate(sorted(raw_tree.nodes(), key=lambda n: sorted(n)))
    }

    bags: Dict[str, Bag] = {}

    def visit(node: FrozenSet[str], parent_node: Optional[FrozenSet[str]]) -> None:
        node_id = bag_ids[node]
        parent_id = bag_ids[parent_node] if parent_node is not None else None
        child_nodes = sorted((n for n in raw_tree.neighbors(node) if n != parent_node), key=lambda n: sorted(n))
        children_ids = tuple(bag_ids[c] for c in child_nodes)
        bags[node_id] = Bag(bag_id=node_id, variables=frozenset(node), parent_id=parent_id, children_ids=children_ids)
        for child_node in child_nodes:
            visit(child_node, node)

    visit(root_node, None)
    return TreeDecomposition(bags=bags, root_id=bag_ids[root_node])
