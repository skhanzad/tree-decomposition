from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from src.fdr.task import State, Task
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import TreeDecomposition
from src.summaries.cache import SummaryCache, compute_fingerprint
from src.summaries.interface import SummaryTable
from src.summaries.local_solver import solve_bag


@dataclass(frozen=True)
class PreprocessResult:
    tables: Dict[str, SummaryTable]
    recomputed_bags: Tuple[str, ...]


def build_initial_cache(
    task: Task,
    decomposition: TreeDecomposition,
    cache: SummaryCache,
    task_version: str,
    state: State | None = None,
) -> PreprocessResult:
    """Bottom-up summary construction for the undisrupted task (offline preprocessing)."""
    current_state = state if state is not None else task.initial_state
    owned = assign_actions(task, decomposition)

    tables: Dict[str, SummaryTable] = {}
    fingerprints: Dict[str, str] = {}
    recomputed: list[str] = []

    for bag_id in decomposition.postorder():
        child_fps = tuple(fingerprints[cid] for cid in decomposition.children_of(bag_id))
        fingerprint = compute_fingerprint(decomposition, bag_id, current_state, owned[bag_id], child_fps)
        fingerprints[bag_id] = fingerprint

        cached = cache.get(bag_id, fingerprint)
        if cached is not None:
            tables[bag_id] = cached
            continue

        child_tables = {cid: tables[cid] for cid in decomposition.children_of(bag_id)}
        goal = task.goal if bag_id == decomposition.root_id else None
        table = solve_bag(
            decomposition=decomposition,
            bag_id=bag_id,
            owned_actions=owned[bag_id],
            current_state=current_state,
            child_tables=child_tables,
            task_version=task_version,
            variables=task.variables,
            goal=goal,
        )
        tables[bag_id] = table
        cache.put(bag_id, fingerprint, table)
        recomputed.append(bag_id)

    return PreprocessResult(tables=tables, recomputed_bags=tuple(recomputed))
