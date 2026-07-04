import pytest

from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from tests.fixtures.two_room_basic import build_task


def test_two_room_basic_decomposes_into_two_bags_with_door_state_separator():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))

    assert len(decomp.bags) == 2
    root_bag = decomp.bag(decomp.root_id)
    assert "robot_B" in root_bag.variables  # root contains the goal variable
    assert root_bag.parent_id is None
    assert len(root_bag.children_ids) == 1

    child_id = root_bag.children_ids[0]
    assert decomp.bag(child_id).variables == frozenset({"robot_A", "door_state"})
    assert decomp.separator_to_parent(child_id) == frozenset({"door_state"})
    assert decomp.separator_to_child(decomp.root_id, child_id) == frozenset({"door_state"})
    assert decomp.postorder() == (child_id, decomp.root_id)


def test_find_bag_by_variables():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    found = decomp.find_bag(frozenset({"robot_A", "door_state"}))
    assert decomp.bag(found).variables == frozenset({"robot_A", "door_state"})


def test_build_decomposition_raises_if_no_bag_covers_goal():
    task = build_task()
    graph = build_interaction_graph(task)
    graph.remove_node("robot_B")  # sabotage: goal variable no longer in any bag
    with pytest.raises(ValueError):
        build_decomposition(task, graph)
