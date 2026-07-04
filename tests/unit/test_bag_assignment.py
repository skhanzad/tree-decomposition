import pytest

from src.fdr.task import Action, Task, Variable
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from tests.fixtures.two_room_basic import (
    ALL_ACTIONS,
    ENTER_B,
    EXIT_B,
    GOTO_DOOR_A,
    GOTO_DOOR_B,
    GOTO_HOME_A,
    GOTO_HOME_B,
    LOCK_DOOR,
    UNLOCK_DOOR,
    build_task,
)


def test_every_action_assigned_exactly_once_to_a_covering_bag():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)

    all_assigned = [a for actions in owned.values() for a in actions]
    assert len(all_assigned) == len(ALL_ACTIONS)
    assert set(all_assigned) == set(ALL_ACTIONS)

    for bag_id, actions in owned.items():
        bag_vars = decomp.bag(bag_id).variables
        for action in actions:
            assert action.scope <= bag_vars

    room_a_bag = decomp.find_bag(frozenset({"robot_A", "door_state"}))
    room_b_bag = decomp.root_id
    assert set(owned[room_a_bag]) == {GOTO_DOOR_A, GOTO_HOME_A, UNLOCK_DOOR, LOCK_DOOR}
    assert set(owned[room_b_bag]) == {GOTO_DOOR_B, GOTO_HOME_B, ENTER_B, EXIT_B}


def test_assign_actions_raises_if_scope_uncovered():
    v1 = Variable(name="x", domain=frozenset({"0", "1"}))
    v2 = Variable(name="y", domain=frozenset({"0", "1"}))
    unreachable_action = Action.create("touch_both", {"x": "0", "y": "0"}, {"x": "1"})
    task = Task.create(variables=(v1, v2), actions=(unreachable_action,), initial_state={"x": "0", "y": "0"}, goal={"x": "1"})
    graph = build_interaction_graph(task)
    decomp = build_decomposition(task, graph)
    # sabotage: pretend the action needs a variable no bag has
    bad_action = Action.create("touch_ghost", {"x": "0", "ghost": "0"}, {"x": "1"})
    bad_task = Task.create(variables=(v1, v2), actions=(bad_action,), initial_state={"x": "0", "y": "0"}, goal={"x": "1"})
    with pytest.raises(ValueError):
        assign_actions(bad_task, decomp)
