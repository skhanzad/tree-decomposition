# tests/property/test_cache_correctness.py
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.repair.disruption import ActionUnavailable
from src.repair.localized_repair import repair
from src.summaries.cache import SummaryCache
from tests.fixtures import three_room_hub


def test_unrelated_sibling_subtree_is_never_invalidated():
    """CLAUDE.md §15 property #4: a disruption with no path to a bag's dependencies
    never invalidates that bag. three_room_hub's bag_A and bag_C are independent
    siblings under the root, connected only through the hub separator."""
    task = three_room_hub.build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    bag_a = decomp.find_bag(frozenset({"hub", "robot_A"}))
    bag_c = decomp.find_bag(frozenset({"hub", "robot_C"}))

    for disrupted_action, untouched_bag in [("work_C", bag_a), ("mark_C", bag_a), ("work_A", bag_c), ("mark_A", bag_c)]:
        cache = SummaryCache.empty()
        # warm the cache first with an unrelated no-op-ish disruption on the root's own variable
        from src.repair.disruption import StateFactChange

        repair(task, decomp, task.initial_state, StateFactChange("robot_D", "start"), cache, task_version="v1")

        result = repair(task, decomp, task.initial_state, ActionUnavailable(disrupted_action), cache, task_version="v1")
        assert untouched_bag in result.log.reused_bags, (disrupted_action, untouched_bag)
        assert untouched_bag not in result.log.recomputed_bags


def test_reused_summary_never_reused_after_its_own_dependency_changes():
    """A bag whose own owned action becomes unavailable must never be served from cache."""
    task = three_room_hub.build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    bag_a = decomp.find_bag(frozenset({"hub", "robot_A"}))
    cache = SummaryCache.empty()

    from src.repair.disruption import StateFactChange

    repair(task, decomp, task.initial_state, StateFactChange("robot_D", "start"), cache, task_version="v1")
    result = repair(task, decomp, task.initial_state, ActionUnavailable("work_A"), cache, task_version="v1")

    assert bag_a in result.log.recomputed_bags
    assert bag_a not in result.log.reused_bags
