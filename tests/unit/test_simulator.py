import pytest

from src.fdr.simulator import apply_action, is_applicable, is_goal, validate_plan
from src.fdr.task import Action, State, Task, Variable


def _tiny_task() -> Task:
    v = Variable(name="loc", domain=frozenset({"A", "B"}))
    move = Action.create("move", {"loc": "A"}, {"loc": "B"})
    return Task.create(variables=(v,), actions=(move,), initial_state={"loc": "A"}, goal={"loc": "B"})


def test_is_applicable_true_and_false():
    task = _tiny_task()
    move = next(iter(task.actions))
    assert is_applicable(move, task.initial_state) is True
    assert is_applicable(move, State.create({"loc": "B"})) is False


def test_apply_action_returns_new_state():
    task = _tiny_task()
    move = next(iter(task.actions))
    result = apply_action(move, task.initial_state)
    assert result.get("loc") == "B"


def test_apply_action_raises_when_inapplicable():
    task = _tiny_task()
    move = next(iter(task.actions))
    with pytest.raises(ValueError):
        apply_action(move, State.create({"loc": "B"}))


def test_is_goal():
    task = _tiny_task()
    assert is_goal(task, task.initial_state) is False
    assert is_goal(task, State.create({"loc": "B"})) is True


def test_validate_plan_success_and_failure():
    task = _tiny_task()
    move = next(iter(task.actions))
    assert validate_plan(task, (move,)) is True
    assert validate_plan(task, ()) is False
    assert validate_plan(task, (move, move)) is False  # second move inapplicable from loc=B
