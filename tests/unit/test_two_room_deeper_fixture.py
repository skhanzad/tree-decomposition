from src.fdr.simulator import validate_plan
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from tests.fixtures.two_room_deeper import (
    CROSS_HALLWAY,
    GOTO_EXIT_A,
    GOTO_EXIT_B,
    OPEN_GATE_A,
    OPEN_GATE_B,
    build_task,
)


def test_known_optimal_plan_validates():
    task = build_task()
    plan = (GOTO_EXIT_A, OPEN_GATE_A, CROSS_HALLWAY, OPEN_GATE_B, GOTO_EXIT_B)
    assert validate_plan(task, plan) is True
    assert sum(a.cost for a in plan) == 5


def test_decomposes_into_four_bag_chain():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    assert len(decomp.bags) == 4
    # exactly one bag per rooted level, single-child chain all the way down
    depths = set()
    bag_id = decomp.root_id
    while True:
        depths.add(bag_id)
        children = decomp.children_of(bag_id)
        if not children:
            break
        assert len(children) == 1
        bag_id = children[0]
    assert len(depths) == 4
