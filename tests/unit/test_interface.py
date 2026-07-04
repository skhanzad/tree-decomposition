from src.fdr.task import Action
from src.summaries.interface import (
    ChildJumpStep,
    OwnActionStep,
    SummaryEntry,
    SummaryTable,
    make_interface,
)


def test_make_interface_sorts_pairs():
    assert make_interface({"b": "2", "a": "1"}) == (("a", "1"), ("b", "2"))


def test_summary_table_get_and_best_outgoing_filters_infeasible():
    action = Action.create("noop", {}, {})
    incoming = (("door_state", "locked"),)
    feasible_entry = SummaryEntry(
        feasible=True,
        cost=2.0,
        local_plan_fragment=(OwnActionStep(action),),
        child_interface_choices=(),
        bag_id="bag_A",
        task_version="v1",
    )
    infeasible_entry = SummaryEntry(
        feasible=False,
        cost=float("inf"),
        local_plan_fragment=(),
        child_interface_choices=(),
        bag_id="bag_A",
        task_version="v1",
    )
    table = SummaryTable.create(
        "bag_A",
        {
            (incoming, (("door_state", "unlocked"),)): feasible_entry,
            (incoming, (("door_state", "locked"),)): infeasible_entry,
        },
    )
    assert table.get(incoming, (("door_state", "unlocked"),)) is feasible_entry
    best = table.best_outgoing(incoming)
    assert best == {(("door_state", "unlocked"),): feasible_entry}


def test_child_jump_step_fields():
    step = ChildJumpStep(child_bag_id="bag_A", incoming=(("x", "0"),), outgoing=(("x", "1"),))
    assert step.child_bag_id == "bag_A"
    assert step.incoming == (("x", "0"),)
