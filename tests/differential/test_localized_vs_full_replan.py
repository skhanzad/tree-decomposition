# tests/differential/test_localized_vs_full_replan.py
import pytest

from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.repair.disruption import ActionUnavailable, StateFactChange
from src.repair.full_replan import full_replan
from src.repair.localized_repair import repair
from src.summaries.cache import SummaryCache
from tests.fixtures import three_room_hub, two_room_basic, two_room_deeper

SCENARIOS = [
    (two_room_basic, StateFactChange(variable="door_state", new_value="unlocked")),
    (two_room_basic, StateFactChange(variable="door_state", new_value="locked")),
    (two_room_basic, ActionUnavailable(action_name="unlock_door")),
    (two_room_basic, ActionUnavailable(action_name="goto_door_B")),
    (two_room_deeper, StateFactChange(variable="gate_A", new_value="open")),
    (two_room_deeper, StateFactChange(variable="hallway_pos", new_value="right")),
    (two_room_deeper, ActionUnavailable(action_name="cross_hallway")),
    (two_room_deeper, ActionUnavailable(action_name="open_gate_B")),
    (three_room_hub, StateFactChange(variable="hub", new_value="marked")),
    (three_room_hub, ActionUnavailable(action_name="work_A")),
    (three_room_hub, ActionUnavailable(action_name="work_C")),
    (three_room_hub, ActionUnavailable(action_name="mark_A")),
]


@pytest.mark.parametrize("fixture_module,disruption", SCENARIOS)
def test_localized_repair_agrees_with_full_replan(fixture_module, disruption):
    task = fixture_module.build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    cache = SummaryCache.empty()

    localized = repair(task, decomp, task.initial_state, disruption, cache, task_version="v1")

    from src.repair.disruption import apply_disruption

    oracle_task, oracle_state = apply_disruption(task, task.initial_state, disruption)
    oracle_plan = full_replan(oracle_task, start=oracle_state)

    localized_feasible = localized.plan is not None
    oracle_feasible = oracle_plan is not None
    assert localized_feasible == oracle_feasible, (fixture_module.__name__, disruption)

    if localized_feasible:
        assert localized.log.plan_valid is True
        oracle_cost = sum(a.cost for a in oracle_plan)
        assert localized.cost == oracle_cost, (fixture_module.__name__, disruption)
    else:
        # The fallback to full_replan would independently reach the same (correct)
        # infeasible verdict even if the tree-decomposition summary machinery were
        # broken, which would silently mask a bug in root-feasibility detection.
        # Require root_feasible=False specifically, so this assertion is exercising
        # the summary composition path itself, not just the fallback's own oracle call.
        assert localized.log.root_feasible is False, (fixture_module.__name__, disruption)
