from src.fdr.simulator import validate_plan
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from tests.fixtures.three_room_hub import FINISH_D, MARK_A, WORK_A, build_task


def test_known_optimal_plan_validates():
    task = build_task()
    plan = (WORK_A, MARK_A, FINISH_D)
    assert validate_plan(task, plan) is True
    assert sum(a.cost for a in plan) == 3


def test_decomposes_with_root_having_two_independent_children():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    assert len(decomp.bags) == 3
    root = decomp.bag(decomp.root_id)
    assert root.variables == frozenset({"hub", "robot_D"})
    assert len(root.children_ids) == 2
    child_var_sets = {decomp.bag(c).variables for c in root.children_ids}
    assert child_var_sets == {frozenset({"hub", "robot_A"}), frozenset({"hub", "robot_C"})}
    # the two children share no variables with each other except through the root's hub
    for c in root.children_ids:
        assert decomp.children_of(c) == ()
