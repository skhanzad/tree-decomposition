from src.repair.disruption import ActionUnavailable, StateFactChange, apply_disruption
from tests.fixtures.two_room_basic import build_task


def test_state_fact_change_updates_state_only():
    task = build_task()
    disruption = StateFactChange(variable="door_state", new_value="unlocked")
    new_task, new_state = apply_disruption(task, task.initial_state, disruption)
    assert new_task is task
    assert new_state.get("door_state") == "unlocked"


def test_action_unavailable_removes_action_only():
    task = build_task()
    disruption = ActionUnavailable(action_name="unlock_door")
    new_task, new_state = apply_disruption(task, task.initial_state, disruption)
    assert new_state == task.initial_state
    assert "unlock_door" not in {a.name for a in new_task.actions}
    assert len(new_task.actions) == len(task.actions) - 1
