"""Milestone 1 toy domain: room A -- hallway -- room B, a 5-variable path.

The interaction graph robot_A-gate_A-hallway_pos-gate_B-robot_B is already chordal,
so the automatic min-fill decomposition returns a 4-bag chain (one bag per edge),
testing propagation through two intermediate bags instead of just one.
"""
from src.fdr.task import Action, Task, Variable

ROBOT_A = Variable(name="robot_A", domain=frozenset({"home", "exit"}))
GATE_A = Variable(name="gate_A", domain=frozenset({"closed", "open"}))
HALLWAY_POS = Variable(name="hallway_pos", domain=frozenset({"left", "right"}))
GATE_B = Variable(name="gate_B", domain=frozenset({"closed", "open"}))
ROBOT_B = Variable(name="robot_B", domain=frozenset({"home", "exit"}))

GOTO_EXIT_A = Action.create("goto_exit_A", {"robot_A": "home"}, {"robot_A": "exit"})
OPEN_GATE_A = Action.create("open_gate_A", {"robot_A": "exit"}, {"gate_A": "open"})
CROSS_HALLWAY = Action.create("cross_hallway", {"gate_A": "open", "hallway_pos": "left"}, {"hallway_pos": "right"})
OPEN_GATE_B = Action.create("open_gate_B", {"hallway_pos": "right"}, {"gate_B": "open"})
GOTO_EXIT_B = Action.create("goto_exit_B", {"gate_B": "open", "robot_B": "home"}, {"robot_B": "exit"})

ALL_ACTIONS = (GOTO_EXIT_A, OPEN_GATE_A, CROSS_HALLWAY, OPEN_GATE_B, GOTO_EXIT_B)


def build_task() -> Task:
    return Task.create(
        variables=(ROBOT_A, GATE_A, HALLWAY_POS, GATE_B, ROBOT_B),
        actions=ALL_ACTIONS,
        initial_state={
            "robot_A": "home",
            "gate_A": "closed",
            "hallway_pos": "left",
            "gate_B": "closed",
            "robot_B": "home",
        },
        goal={"robot_B": "exit"},
    )
