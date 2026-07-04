from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.repair.disruption import ActionUnavailable, StateFactChange
from src.summaries.invalidation import directly_affected_bags, expand_to_affected_subtree
from tests.fixtures.three_room_hub import build_task as build_hub_task
from tests.fixtures.two_room_deeper import build_task as build_deeper_task


def test_leaf_disruption_propagates_to_every_ancestor_in_a_chain():
    task = build_deeper_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)
    leaf_bag = decomp.find_bag(frozenset({"robot_A", "gate_A"}))

    disruption = StateFactChange(variable="robot_A", new_value="exit")
    directly = directly_affected_bags(decomp, owned, disruption)
    assert directly == frozenset({leaf_bag})

    subtree = expand_to_affected_subtree(decomp, directly)
    assert subtree == frozenset(decomp.bags.keys())  # every bag is on the chain from leaf to root


def test_disrupting_one_hub_child_never_invalidates_its_sibling():
    task = build_hub_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)
    bag_c = decomp.find_bag(frozenset({"hub", "robot_C"}))
    bag_a = decomp.find_bag(frozenset({"hub", "robot_A"}))

    disruption = ActionUnavailable(action_name="work_C")
    directly = directly_affected_bags(decomp, owned, disruption)
    assert directly == frozenset({bag_c})

    subtree = expand_to_affected_subtree(decomp, directly)
    assert subtree == frozenset({bag_c, decomp.root_id})
    assert bag_a not in subtree
