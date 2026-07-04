"""Milestone 1 toy domain: two independent rooms (A, C) coordinating through one
shared hub variable, with a third room (D) whose goal depends on the hub being marked.

Interaction graph is a 3-leaf star centered on hub, so the decomposition is a root
bag {hub, robot_D} with two independent children {hub, robot_A} and {hub, robot_C} --
the branching structure needed to test that disrupting one child never invalidates
its unrelated sibling.
"""
from src.fdr.task import Action, Task, Variable

HUB = Variable(name="hub", domain=frozenset({"free", "marked"}))
ROBOT_A = Variable(name="robot_A", domain=frozenset({"start", "end"}))
ROBOT_C = Variable(name="robot_C", domain=frozenset({"start", "end"}))
ROBOT_D = Variable(name="robot_D", domain=frozenset({"start", "done"}))

WORK_A = Action.create("work_A", {"hub": "free", "robot_A": "start"}, {"robot_A": "end"})
MARK_A = Action.create("mark_A", {"robot_A": "end"}, {"hub": "marked"})
WORK_C = Action.create("work_C", {"hub": "free", "robot_C": "start"}, {"robot_C": "end"})
MARK_C = Action.create("mark_C", {"robot_C": "end"}, {"hub": "marked"})
FINISH_D = Action.create("finish_D", {"hub": "marked", "robot_D": "start"}, {"robot_D": "done"})

ALL_ACTIONS = (WORK_A, MARK_A, WORK_C, MARK_C, FINISH_D)


def build_task() -> Task:
    return Task.create(
        variables=(HUB, ROBOT_A, ROBOT_C, ROBOT_D),
        actions=ALL_ACTIONS,
        initial_state={"hub": "free", "robot_A": "start", "robot_C": "start", "robot_D": "start"},
        goal={"robot_D": "done"},
    )
