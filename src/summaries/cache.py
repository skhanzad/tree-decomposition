from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from src.fdr.task import Action, State
from src.graph.decomposition import TreeDecomposition
from src.summaries.interface import SummaryTable


def compute_fingerprint(
    decomposition: TreeDecomposition,
    bag_id: str,
    state: State,
    owned_actions: Tuple[Action, ...],
    child_fingerprints: Tuple[str, ...],
) -> str:
    bag = decomposition.bag(bag_id)
    parent_sep = decomposition.separator_to_parent(bag_id)
    relevant_vars = sorted(bag.variables - parent_sep)
    action_sig = tuple(sorted((a.name, a.precondition, a.effect, a.cost) for a in owned_actions))
    state_sig = tuple((v, state.get(v)) for v in relevant_vars)
    payload = (bag_id, action_sig, state_sig, tuple(sorted(child_fingerprints)))
    return repr(payload)


@dataclass
class SummaryCache:
    _tables: Dict[str, SummaryTable] = field(default_factory=dict)
    _fingerprints: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def empty() -> "SummaryCache":
        return SummaryCache()

    def get(self, bag_id: str, fingerprint: str) -> Optional[SummaryTable]:
        if self._fingerprints.get(bag_id) == fingerprint:
            return self._tables.get(bag_id)
        return None

    def put(self, bag_id: str, fingerprint: str, table: SummaryTable) -> None:
        self._tables[bag_id] = table
        self._fingerprints[bag_id] = fingerprint

    def invalidate(self, bag_id: str) -> None:
        self._tables.pop(bag_id, None)
        self._fingerprints.pop(bag_id, None)
