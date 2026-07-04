# tests/unit/test_compose.py
from src.fdr.simulator import validate_plan
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.summaries.compose import compute_all_summaries, extract_plan
from tests.fixtures import three_room_hub, two_room_basic, two_room_deeper


def _run(task_module):
    task = task_module.build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    tables = compute_all_summaries(task, decomp, task.initial_state, task_version="v1")
    root_entry = tables[decomp.root_id].get((), ())
    return task, root_entry, tables


def test_two_room_basic_end_to_end_plan_is_valid_and_optimal():
    task, root_entry, tables = _run(two_room_basic)
    assert root_entry.feasible is True
    assert root_entry.cost == 4
    plan = extract_plan(tables, root_entry)
    assert len(plan) == 4
    assert validate_plan(task, plan) is True


def test_two_room_deeper_end_to_end_plan_is_valid_and_optimal():
    task, root_entry, tables = _run(two_room_deeper)
    assert root_entry.feasible is True
    assert root_entry.cost == 5
    plan = extract_plan(tables, root_entry)
    assert validate_plan(task, plan) is True


def test_three_room_hub_end_to_end_plan_is_valid_and_optimal():
    task, root_entry, tables = _run(three_room_hub)
    assert root_entry.feasible is True
    assert root_entry.cost == 3
    plan = extract_plan(tables, root_entry)
    assert validate_plan(task, plan) is True
