from __future__ import annotations

from typing import Optional, Sequence

from src.fdr.task import Action, State, Task


def is_applicable(action: Action, state: State) -> bool:
    return all(state.get(var) == val for var, val in action.precondition)


def apply_action(action: Action, state: State) -> State:
    if not is_applicable(action, state):
        raise ValueError(f"action {action.name!r} is not applicable in state {dict(state.assignment)}")
    return state.with_updates(dict(action.effect))


def is_goal(task: Task, state: State) -> bool:
    return all(state.get(var) == val for var, val in task.goal)


def validate_plan(task: Task, plan: Sequence[Action], start: Optional[State] = None) -> bool:
    state = start if start is not None else task.initial_state
    for action in plan:
        if not is_applicable(action, state):
            return False
        state = apply_action(action, state)
    return is_goal(task, state)
