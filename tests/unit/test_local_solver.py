from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.summaries.local_solver import solve_bag
from tests.fixtures.two_room_basic import build_task


def test_leaf_bag_a_table_matches_hand_derivation():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)
    bag_a_id = decomp.find_bag(frozenset({"robot_A", "door_state"}))

    table = solve_bag(
        decomposition=decomp,
        bag_id=bag_a_id,
        owned_actions=owned[bag_a_id],
        current_state=task.initial_state,
        child_tables={},
        task_version="v1",
        variables=task.variables,
    )

    locked = (("door_state", "locked"),)
    unlocked = (("door_state", "unlocked"),)

    assert table.get(locked, locked).cost == 0
    assert table.get(locked, unlocked).cost == 2
    assert table.get(unlocked, unlocked).cost == 0
    assert table.get(unlocked, locked).cost == 2
    for entry in table.entries.values():
        assert entry.feasible is True


def test_root_bag_b_reaches_goal_at_cost_four_via_child_jump():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)
    bag_a_id = decomp.find_bag(frozenset({"robot_A", "door_state"}))

    bag_a_table = solve_bag(
        decomposition=decomp,
        bag_id=bag_a_id,
        owned_actions=owned[bag_a_id],
        current_state=task.initial_state,
        child_tables={},
        task_version="v1",
        variables=task.variables,
    )

    root_table = solve_bag(
        decomposition=decomp,
        bag_id=decomp.root_id,
        owned_actions=owned[decomp.root_id],
        current_state=task.initial_state,
        child_tables={bag_a_id: bag_a_table},
        task_version="v1",
        variables=task.variables,
        goal=task.goal,
    )

    root_entry = root_table.get((), ())
    assert root_entry.feasible is True
    assert root_entry.cost == 4
