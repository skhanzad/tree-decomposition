from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Mapping, Tuple

Assignment = Tuple[Tuple[str, str], ...]


def _to_assignment(d: Mapping[str, str]) -> Assignment:
    return tuple(sorted(d.items()))


@dataclass(frozen=True)
class Variable:
    name: str
    domain: FrozenSet[str]


@dataclass(frozen=True)
class Action:
    name: str
    precondition: Assignment
    effect: Assignment
    cost: int = 1

    @staticmethod
    def create(
        name: str,
        precondition: Mapping[str, str],
        effect: Mapping[str, str],
        cost: int = 1,
    ) -> "Action":
        return Action(
            name=name,
            precondition=_to_assignment(precondition),
            effect=_to_assignment(effect),
            cost=cost,
        )

    @property
    def scope(self) -> FrozenSet[str]:
        return frozenset(dict(self.precondition)) | frozenset(dict(self.effect))


@dataclass(frozen=True)
class State:
    assignment: Assignment

    @staticmethod
    def create(d: Mapping[str, str]) -> "State":
        return State(_to_assignment(d))

    def get(self, var: str) -> str:
        for k, v in self.assignment:
            if k == var:
                return v
        raise KeyError(var)

    def with_updates(self, updates: Mapping[str, str]) -> "State":
        d = dict(self.assignment)
        d.update(updates)
        return State.create(d)


@dataclass(frozen=True)
class Task:
    variables: FrozenSet[Variable]
    actions: FrozenSet[Action]
    initial_state: State
    goal: Assignment

    @staticmethod
    def create(
        variables: Iterable[Variable],
        actions: Iterable[Action],
        initial_state: Mapping[str, str],
        goal: Mapping[str, str],
    ) -> "Task":
        return Task(
            variables=frozenset(variables),
            actions=frozenset(actions),
            initial_state=State.create(initial_state),
            goal=_to_assignment(goal),
        )

    def variable_names(self) -> FrozenSet[str]:
        return frozenset(v.name for v in self.variables)
