"""Milestone 1 toy domain: two rooms connected by exactly one shared variable.

Bag A (room A) = {robot_A, door_state}; Bag B (room B) = {door_state, robot_B}.
door_state is the only separator variable between the two bags.
"""
from src.fdr.task import Action, Task, Variable

ROBOT_A = Variable(name="robot_A", domain=frozenset({"home", "door"}))
DOOR_STATE = Variable(name="door_state", domain=frozenset({"locked", "unlocked"}))
ROBOT_B = Variable(name="robot_B", domain=frozenset({"home", "door", "beyond"}))

GOTO_DOOR_A = Action.create("goto_door_A", {"robot_A": "home"}, {"robot_A": "door"})
GOTO_HOME_A = Action.create("goto_home_A", {"robot_A": "door"}, {"robot_A": "home"})
UNLOCK_DOOR = Action.create("unlock_door", {"robot_A": "door"}, {"door_state": "unlocked"})
LOCK_DOOR = Action.create("lock_door", {"robot_A": "door"}, {"door_state": "locked"})
GOTO_DOOR_B = Action.create("goto_door_B", {"robot_B": "home"}, {"robot_B": "door"})
GOTO_HOME_B = Action.create("goto_home_B", {"robot_B": "door"}, {"robot_B": "home"})
ENTER_B = Action.create("enter_B", {"robot_B": "door", "door_state": "unlocked"}, {"robot_B": "beyond"})
EXIT_B = Action.create("exit_B", {"robot_B": "beyond"}, {"robot_B": "door"})

ALL_ACTIONS = (GOTO_DOOR_A, GOTO_HOME_A, UNLOCK_DOOR, LOCK_DOOR, GOTO_DOOR_B, GOTO_HOME_B, ENTER_B, EXIT_B)


def build_task() -> Task:
    return Task.create(
        variables=(ROBOT_A, DOOR_STATE, ROBOT_B),
        actions=ALL_ACTIONS,
        initial_state={"robot_A": "home", "door_state": "locked", "robot_B": "home"},
        goal={"robot_B": "beyond"},
    )
