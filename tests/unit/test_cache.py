# tests/unit/test_cache.py
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.summaries.cache import SummaryCache, compute_fingerprint
from src.summaries.interface import SummaryTable
from tests.fixtures.two_room_basic import build_task


def _bag_a_setup():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)
    bag_a_id = decomp.find_bag(frozenset({"robot_A", "door_state"}))
    return task, decomp, owned, bag_a_id


def test_fingerprint_unchanged_when_irrelevant_state_unchanged():
    task, decomp, owned, bag_a_id = _bag_a_setup()
    fp1 = compute_fingerprint(decomp, bag_a_id, task.initial_state, owned[bag_a_id], ())
    fp2 = compute_fingerprint(decomp, bag_a_id, task.initial_state, owned[bag_a_id], ())
    assert fp1 == fp2


def test_fingerprint_changes_when_bag_local_variable_changes():
    task, decomp, owned, bag_a_id = _bag_a_setup()
    fp_before = compute_fingerprint(decomp, bag_a_id, task.initial_state, owned[bag_a_id], ())
    changed_state = task.initial_state.with_updates({"robot_A": "door"})
    fp_after = compute_fingerprint(decomp, bag_a_id, changed_state, owned[bag_a_id], ())
    assert fp_before != fp_after


def test_fingerprint_unaffected_by_parent_separator_value():
    # door_state is bag_A's PARENT separator: its real current value must not affect
    # bag_A's fingerprint, since the local solver hypothesizes over all its domain values anyway.
    task, decomp, owned, bag_a_id = _bag_a_setup()
    fp_locked = compute_fingerprint(decomp, bag_a_id, task.initial_state, owned[bag_a_id], ())
    unlocked_state = task.initial_state.with_updates({"door_state": "unlocked"})
    fp_unlocked = compute_fingerprint(decomp, bag_a_id, unlocked_state, owned[bag_a_id], ())
    assert fp_locked == fp_unlocked


def test_cache_put_get_roundtrip_and_invalidate():
    cache = SummaryCache.empty()
    table = SummaryTable.create("bag_A", {})
    cache.put("bag_A", "fp1", table)
    assert cache.get("bag_A", "fp1") is table
    assert cache.get("bag_A", "fp2") is None  # fingerprint mismatch -> cache miss
    cache.invalidate("bag_A")
    assert cache.get("bag_A", "fp1") is None
