from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Mapping, Optional, Tuple, Union

from src.fdr.task import Action

InterfaceAssignment = Tuple[Tuple[str, str], ...]


def make_interface(d: Mapping[str, str]) -> InterfaceAssignment:
    return tuple(sorted(d.items()))


@dataclass(frozen=True)
class OwnActionStep:
    action: Action


@dataclass(frozen=True)
class ChildJumpStep:
    child_bag_id: str
    incoming: InterfaceAssignment
    outgoing: InterfaceAssignment


PlanStep = Union[OwnActionStep, ChildJumpStep]


@dataclass(frozen=True)
class SummaryEntry:
    feasible: bool
    cost: float
    local_plan_fragment: Tuple[PlanStep, ...]
    child_interface_choices: Tuple[Tuple[str, InterfaceAssignment, InterfaceAssignment], ...]
    bag_id: str
    task_version: str


@dataclass(frozen=True)
class SummaryTable:
    bag_id: str
    entries: Mapping[Tuple[InterfaceAssignment, InterfaceAssignment], SummaryEntry]

    @staticmethod
    def create(
        bag_id: str,
        entries: Dict[Tuple[InterfaceAssignment, InterfaceAssignment], SummaryEntry],
    ) -> "SummaryTable":
        return SummaryTable(bag_id=bag_id, entries=MappingProxyType(dict(entries)))

    def get(self, incoming: InterfaceAssignment, outgoing: InterfaceAssignment) -> Optional[SummaryEntry]:
        return self.entries.get((incoming, outgoing))

    def best_outgoing(self, incoming: InterfaceAssignment) -> Dict[InterfaceAssignment, SummaryEntry]:
        return {o: e for (i, o), e in self.entries.items() if i == incoming and e.feasible}
