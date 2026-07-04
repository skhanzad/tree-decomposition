from src.fdr.simulator import validate_plan
from src.repair.full_replan import full_replan
from tests.fixtures import three_room_hub, two_room_basic, two_room_deeper


def test_two_room_basic_full_replan_matches_known_optimum():
    task = two_room_basic.build_task()
    plan = full_replan(task)
    assert plan is not None
    assert sum(a.cost for a in plan) == 4
    assert validate_plan(task, plan) is True


def test_two_room_deeper_full_replan_matches_known_optimum():
    task = two_room_deeper.build_task()
    plan = full_replan(task)
    assert plan is not None
    assert sum(a.cost for a in plan) == 5


def test_three_room_hub_full_replan_matches_known_optimum():
    task = three_room_hub.build_task()
    plan = full_replan(task)
    assert plan is not None
    assert sum(a.cost for a in plan) == 3


def test_full_replan_returns_none_when_unreachable():
    task = two_room_basic.build_task()
    unreachable_actions = frozenset(a for a in task.actions if a.name != "unlock_door")
    from src.fdr.task import Task as TaskType

    sabotaged = TaskType(
        variables=task.variables, actions=unreachable_actions, initial_state=task.initial_state, goal=task.goal
    )
    assert full_replan(sabotaged) is None
