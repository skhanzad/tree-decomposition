from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.repair.disruption import ActionUnavailable, StateFactChange
from src.repair.localized_repair import repair
from src.summaries.cache import SummaryCache
from tests.fixtures import three_room_hub, two_room_basic


def test_state_fact_change_repairs_and_reuses_cache_on_second_call():
    task = two_room_basic.build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    cache = SummaryCache.empty()

    disruption = StateFactChange(variable="door_state", new_value="unlocked")
    result = repair(task, decomp, task.initial_state, disruption, cache, task_version="v1")

    assert result.log.root_feasible is True
    assert result.log.fallback_occurred is False
    assert result.log.plan_valid is True
    assert result.cost == 2  # door already unlocked: goto_door_B, enter_B


def test_action_unavailable_making_goal_unreachable_falls_back_and_agrees_with_full_replan():
    task = two_room_basic.build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    cache = SummaryCache.empty()

    disruption = ActionUnavailable(action_name="unlock_door")
    result = repair(task, decomp, task.initial_state, disruption, cache, task_version="v1")

    assert result.log.root_feasible is False
    assert result.log.fallback_occurred is True
    assert result.plan is None  # full_replan also finds no plan


def test_disrupting_hub_child_c_reuses_sibling_bag_a_from_cache():
    task = three_room_hub.build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    cache = SummaryCache.empty()

    # first solve to populate the cache with no disruption applied
    from src.repair.disruption import StateFactChange as _NoOpMarker  # noqa: F401 (documents intent below)

    bag_a = decomp.find_bag(frozenset({"hub", "robot_A"}))
    bag_c = decomp.find_bag(frozenset({"hub", "robot_C"}))

    warm_disruption = StateFactChange(variable="robot_D", new_value="start")  # no-op value, just to populate cache
    repair(task, decomp, task.initial_state, warm_disruption, cache, task_version="v1")

    disruption = ActionUnavailable(action_name="work_C")
    result = repair(task, decomp, task.initial_state, disruption, cache, task_version="v1")

    assert result.log.root_feasible is True
    assert result.cost == 3  # still reachable via room A
    assert bag_a in result.log.reused_bags
    assert bag_c in result.log.recomputed_bags
    assert decomp.root_id in result.log.recomputed_bags


def test_repair_package_exports_are_reachable_via_package_import():
    """Regression guard for the circular-import fix in src/repair/__init__.py:
    src/summaries/__init__.py -> invalidation -> repair.disruption -> repair/__init__.py
    -> localized_repair -> back into src.summaries.* forms a real cycle if
    RepairLog/RepairResult/repair are imported eagerly at repair/__init__.py's
    module scope, so they're exposed lazily via __getattr__ instead. This test
    would fail with an ImportError (not an AssertionError) if that lazy export
    were ever "simplified" back to eager imports.
    """
    import src.repair as repair_package

    assert repair_package.repair is repair
    assert repair_package.RepairLog.__name__ == "RepairLog"
    assert repair_package.RepairResult.__name__ == "RepairResult"
