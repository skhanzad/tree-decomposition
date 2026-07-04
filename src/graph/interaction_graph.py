from __future__ import annotations

import networkx as nx

from src.fdr.task import Task


def build_interaction_graph(task: Task) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(v.name for v in task.variables)
    for action in task.actions:
        scope = sorted(action.scope)
        for i in range(len(scope)):
            for j in range(i + 1, len(scope)):
                graph.add_edge(scope[i], scope[j])
    return graph
