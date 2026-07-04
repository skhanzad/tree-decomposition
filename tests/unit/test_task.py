import pytest

from src.fdr.task import Action, State, Task, Variable


def test_action_create_sorts_and_exposes_scope():
    a = Action.create("move", {"loc": "A"}, {"loc": "B"}, cost=2)
    assert a.precondition == (("loc", "A"),)
    assert a.effect == (("loc", "B"),)
    assert a.scope == frozenset({"loc"})
    assert a.cost == 2


def test_state_get_and_with_updates():
    s = State.create({"loc": "A", "held": "false"})
    assert s.get("loc") == "A"
    s2 = s.with_updates({"loc": "B"})
    assert s2.get("loc") == "B"
    assert s2.get("held") == "false"
    assert s.get("loc") == "A"  # original state is untouched (immutability)


def test_state_get_missing_variable_raises_keyerror():
    s = State.create({"loc": "A"})
    with pytest.raises(KeyError):
        s.get("nope")


def test_task_create_builds_sorted_goal_and_variable_names():
    v = Variable(name="loc", domain=frozenset({"A", "B"}))
    a = Action.create("move", {"loc": "A"}, {"loc": "B"})
    task = Task.create(
        variables=(v,),
        actions=(a,),
        initial_state={"loc": "A"},
        goal={"loc": "B"},
    )
    assert task.variable_names() == frozenset({"loc"})
    assert task.goal == (("loc", "B"),)
    assert task.initial_state.get("loc") == "A"


def test_action_and_state_are_hashable():
    a1 = Action.create("move", {"loc": "A"}, {"loc": "B"})
    a2 = Action.create("move", {"loc": "A"}, {"loc": "B"})
    assert hash(a1) == hash(a2)
    assert a1 == a2
    s1 = State.create({"loc": "A"})
    s2 = State.create({"loc": "A"})
    assert hash(s1) == hash(s2)
