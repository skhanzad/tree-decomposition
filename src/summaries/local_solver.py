from __future__ import annotations

import heapq
import itertools
from typing import Dict, FrozenSet, List, Mapping, Optional, Set, Tuple

from src.fdr.task import Action, State, Variable
from src.graph.decomposition import TreeDecomposition
from src.summaries.interface import (
    ChildJumpStep,
    InterfaceAssignment,
    OwnActionStep,
    PlanStep,
    SummaryEntry,
    SummaryTable,
    make_interface,
)

LocalState = Tuple[Tuple[str, str], ...]


def _restrict(state: LocalState, variables: FrozenSet[str]) -> InterfaceAssignment:
    d = dict(state)
    return tuple(sorted((v, d[v]) for v in variables))


def _apply_action(state: LocalState, action: Action) -> Optional[LocalState]:
    d = dict(state)
    for var, val in action.precondition:
        if d.get(var) != val:
            return None
    d.update(dict(action.effect))
    return tuple(sorted(d.items()))


def _domains(bag_vars: Tuple[str, ...], variables: FrozenSet[Variable]) -> Dict[str, Tuple[str, ...]]:
    by_name = {v.name: tuple(sorted(v.domain)) for v in variables}
    return {v: by_name[v] for v in bag_vars}


def solve_bag(
    decomposition: TreeDecomposition,
    bag_id: str,
    owned_actions: Tuple[Action, ...],
    current_state: State,
    child_tables: Mapping[str, SummaryTable],
    task_version: str,
    variables: FrozenSet[Variable],
    goal: Optional[InterfaceAssignment] = None,
) -> SummaryTable:
    bag = decomposition.bag(bag_id)
    is_root = bag.parent_id is None
    if is_root and goal is None:
        raise ValueError(f"goal must be provided when solving the root bag {bag_id!r}")

    bag_vars: Tuple[str, ...] = tuple(sorted(bag.variables))
    parent_sep = decomposition.separator_to_parent(bag_id)
    child_seps = {cid: decomposition.separator_to_child(bag_id, cid) for cid in bag.children_ids}
    domains = _domains(bag_vars, variables)

    fixed_vars = [v for v in bag_vars if v not in parent_sep]
    fixed_values = {v: current_state.get(v) for v in fixed_vars}

    sep_vars = tuple(sorted(parent_sep))
    incoming_options: List[InterfaceAssignment] = (
        [make_interface(dict(zip(sep_vars, combo))) for combo in itertools.product(*(domains[v] for v in sep_vars))]
        if sep_vars
        else [()]
    )

    entries: Dict[Tuple[InterfaceAssignment, InterfaceAssignment], SummaryEntry] = {}

    for incoming in incoming_options:
        start_dict = dict(fixed_values)
        start_dict.update(dict(incoming))
        start: LocalState = tuple(sorted(start_dict.items()))

        dist, prev = _dijkstra(start, owned_actions, child_seps, child_tables)

        if is_root:
            assert goal is not None
            best_state, best_cost = None, float("inf")
            for state, cost in dist.items():
                if cost < best_cost and all(dict(state).get(v) == val for v, val in goal):
                    best_state, best_cost = state, cost
            outgoing: InterfaceAssignment = ()
            entries[(incoming, outgoing)] = _make_entry(
                bag_id, task_version, start, best_state, best_cost, prev
            )
        else:
            best_by_outgoing: Dict[InterfaceAssignment, Tuple[LocalState, float]] = {}
            for state, cost in dist.items():
                outgoing = _restrict(state, parent_sep)
                if outgoing not in best_by_outgoing or cost < best_by_outgoing[outgoing][1]:
                    best_by_outgoing[outgoing] = (state, cost)
            for outgoing, (state, cost) in best_by_outgoing.items():
                entries[(incoming, outgoing)] = _make_entry(bag_id, task_version, start, state, cost, prev)

    return SummaryTable.create(bag_id, entries)


def _dijkstra(
    start: LocalState,
    owned_actions: Tuple[Action, ...],
    child_seps: Mapping[str, FrozenSet[str]],
    child_tables: Mapping[str, SummaryTable],
) -> Tuple[Dict[LocalState, float], Dict[LocalState, Tuple[LocalState, PlanStep]]]:
    dist: Dict[LocalState, float] = {start: 0.0}
    prev: Dict[LocalState, Tuple[LocalState, PlanStep]] = {}
    counter = itertools.count()
    heap: List[Tuple[float, int, LocalState]] = [(0.0, next(counter), start)]
    visited: Set[LocalState] = set()

    while heap:
        cost, _, state = heapq.heappop(heap)
        if state in visited:
            continue
        visited.add(state)

        for action in owned_actions:
            nxt = _apply_action(state, action)
            if nxt is None:
                continue
            new_cost = cost + action.cost
            if new_cost < dist.get(nxt, float("inf")):
                dist[nxt] = new_cost
                prev[nxt] = (state, OwnActionStep(action))
                heapq.heappush(heap, (new_cost, next(counter), nxt))

        for child_id, sep in child_seps.items():
            i_child = _restrict(state, sep)
            for o_child, child_entry in child_tables[child_id].best_outgoing(i_child).items():
                d = dict(state)
                d.update(dict(o_child))
                nxt = tuple(sorted(d.items()))
                new_cost = cost + child_entry.cost
                if new_cost < dist.get(nxt, float("inf")):
                    dist[nxt] = new_cost
                    prev[nxt] = (state, ChildJumpStep(child_id, i_child, o_child))
                    heapq.heappush(heap, (new_cost, next(counter), nxt))

    return dist, prev


def _make_entry(
    bag_id: str,
    task_version: str,
    start: LocalState,
    end: Optional[LocalState],
    cost: float,
    prev: Dict[LocalState, Tuple[LocalState, PlanStep]],
) -> SummaryEntry:
    if end is None:
        return SummaryEntry(
            feasible=False,
            cost=float("inf"),
            local_plan_fragment=(),
            child_interface_choices=(),
            bag_id=bag_id,
            task_version=task_version,
        )
    fragment = _reconstruct(prev, start, end)
    return SummaryEntry(
        feasible=True,
        cost=cost,
        local_plan_fragment=fragment,
        child_interface_choices=_child_choices(fragment),
        bag_id=bag_id,
        task_version=task_version,
    )


def _reconstruct(
    prev: Dict[LocalState, Tuple[LocalState, PlanStep]], start: LocalState, end: LocalState
) -> Tuple[PlanStep, ...]:
    if end == start:
        return ()
    steps: List[PlanStep] = []
    state = end
    while state != start:
        prev_state, step = prev[state]
        steps.append(step)
        state = prev_state
    return tuple(reversed(steps))


def _child_choices(
    fragment: Tuple[PlanStep, ...]
) -> Tuple[Tuple[str, InterfaceAssignment, InterfaceAssignment], ...]:
    return tuple(
        (step.child_bag_id, step.incoming, step.outgoing) for step in fragment if isinstance(step, ChildJumpStep)
    )
