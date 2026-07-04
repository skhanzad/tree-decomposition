# tests/unit/test_two_room_basic_fixture.py
from tests.fixtures.two_room_basic import (
    ENTER_B,
    GOTO_DOOR_A,
    GOTO_DOOR_B,
    UNLOCK_DOOR,
    build_task,
)
from src.fdr.simulator import validate_plan


def test_known_optimal_plan_validates():
    task = build_task()
    plan = (GOTO_DOOR_A, UNLOCK_DOOR, GOTO_DOOR_B, ENTER_B)
    assert validate_plan(task, plan) is True
    assert sum(a.cost for a in plan) == 4


def test_task_scope_is_two_rooms_and_one_separator():
    task = build_task()
    assert task.variable_names() == frozenset({"robot_A", "door_state", "robot_B"})
    assert task.goal == (("robot_B", "beyond"),)
