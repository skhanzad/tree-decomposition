from __future__ import annotations

import heapq
import itertools
from typing import Dict, List, Optional, Set, Tuple

from src.fdr.simulator import apply_action, is_applicable, is_goal
from src.fdr.task import Action, State, Task


def full_replan(task: Task, start: Optional[State] = None) -> Optional[Tuple[Action, ...]]:
    start_state = start if start is not None else task.initial_state
    if is_goal(task, start_state):
        return ()

    dist: Dict[State, float] = {start_state: 0.0}
    prev: Dict[State, Tuple[State, Action]] = {}
    counter = itertools.count()
    heap: List[Tuple[float, int, State]] = [(0.0, next(counter), start_state)]
    visited: Set[State] = set()

    while heap:
        cost, _, state = heapq.heappop(heap)
        if state in visited:
            continue
        visited.add(state)
        if is_goal(task, state):
            return _reconstruct(prev, start_state, state)

        for action in task.actions:
            if not is_applicable(action, state):
                continue
            nxt = apply_action(action, state)
            new_cost = cost + action.cost
            if new_cost < dist.get(nxt, float("inf")):
                dist[nxt] = new_cost
                prev[nxt] = (state, action)
                heapq.heappush(heap, (new_cost, next(counter), nxt))

    return None


def _reconstruct(prev: Dict[State, Tuple[State, Action]], start: State, end: State) -> Tuple[Action, ...]:
    steps: List[Action] = []
    state = end
    while state != start:
        prev_state, action = prev[state]
        steps.append(action)
        state = prev_state
    return tuple(reversed(steps))
