from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Tuple, Union

from src.fdr.task import State, Task


@dataclass(frozen=True)
class StateFactChange:
    variable: str
    new_value: str


@dataclass(frozen=True)
class ActionUnavailable:
    action_name: str


Disruption = Union[StateFactChange, ActionUnavailable]


def affected_variables(disruption: Disruption) -> FrozenSet[str]:
    if isinstance(disruption, StateFactChange):
        return frozenset({disruption.variable})
    return frozenset()


def affected_action_names(disruption: Disruption) -> FrozenSet[str]:
    if isinstance(disruption, ActionUnavailable):
        return frozenset({disruption.action_name})
    return frozenset()


def apply_disruption(task: Task, state: State, disruption: Disruption) -> Tuple[Task, State]:
    if isinstance(disruption, StateFactChange):
        return task, state.with_updates({disruption.variable: disruption.new_value})

    remaining = frozenset(a for a in task.actions if a.name != disruption.action_name)
    new_task = Task(variables=task.variables, actions=remaining, initial_state=task.initial_state, goal=task.goal)
    return new_task, state
