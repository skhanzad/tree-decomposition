from src.graph.interaction_graph import build_interaction_graph
from tests.fixtures.two_room_basic import build_task


def test_two_room_basic_graph_has_expected_edges_only():
    graph = build_interaction_graph(build_task())
    assert set(graph.nodes()) == {"robot_A", "door_state", "robot_B"}
    assert set(frozenset(e) for e in graph.edges()) == {
        frozenset({"robot_A", "door_state"}),
        frozenset({"door_state", "robot_B"}),
    }
    # robot_A and robot_B never co-occur in any action's scope
    assert not graph.has_edge("robot_A", "robot_B")
