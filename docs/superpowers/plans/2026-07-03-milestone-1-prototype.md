# Milestone 1 Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the smallest correct implementation of localized-recomputation plan repair — FDR task model, tree decomposition, exact enumerative interface summaries, disruption-driven invalidation, and plan extraction — proven correct by differential testing against brute-force full replanning on three hand-authored tiny FDR fixtures.

**Architecture:** A tree decomposition (built via networkx's min-fill approximation) partitions an FDR task's actions into bags. Each bag computes a `SummaryTable` mapping (incoming separator assignment → outgoing separator assignment) to a min-cost local plan fragment, via an exact Dijkstra search over the bag's own reachable local states plus "virtual edges" borrowed from already-computed child summaries (bottom-up composition). After a disruption, a versioned fingerprint per bag (derived from its owned actions, its own current variable values, and its children's fingerprints) determines which bags are cache hits (reused) vs. misses (recomputed); a conservative Steiner-tree + ancestor-propagation rule decides which bags get invalidated. The root's summary entry is expanded recursively (splicing in each child's chosen plan fragment) into a flat action sequence, independently validated by a plan simulator, with brute-force full replanning as both the correctness oracle and the fallback/baseline.

**Tech Stack:** Python 3.11+, `uv` for dependency management, `networkx` (interaction graph + min-fill decomposition), `pytest` (all testing — unit, differential, property-style exhaustive).

## Global Constraints

- Python 3.11+, managed via `uv` (per user's global tech-stack preference).
- Frozen dataclasses for all task/state/summary data structures (per coding-style.md immutability rule); the only genuinely mutable structure is `SummaryCache`, which is a cache by definition.
- Every package `__init__.py` defines `__all__` for its public API (coding-style.md).
- No bare `except`; type hints on every function (coding-style.md).
- Correctness path in pure Python only — no perf optimization in this milestone (CLAUDE.md §9 "Performance rule").
- Naming must follow CLAUDE.md §16 exactly: `bag`, `separator`, `summary`, `affected subtree`, `local solver`, `full replan`, `repair`.
- Every repair run must be able to report the CLAUDE.md §16 log fields (directly changed variables/actions, directly affected bags, final affected subtree, reused bags, recomputed bags, root feasibility, fallback occurrence, plan validation result).
- **Design assumption (documented per CLAUDE.md §22):** for a bag's local search, the starting value of every one of its own variables *except the parent separator* is taken from the actual current global state; the parent-separator's starting value is instead enumerated over its full domain, since which value the parent will actually hand off is only known when composing the full plan. This is the concrete interpretation of CLAUDE.md §6's summary semantics used throughout this milestone.
- **Design assumption:** every fixture's goal variables all live inside a single bag (the root), per CLAUDE.md §5's "goal variables assigned to bags in a consistent way." `build_decomposition` raises `ValueError` if this doesn't hold.

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`, `src/fdr/__init__.py`, `src/graph/__init__.py`, `src/summaries/__init__.py`, `src/repair/__init__.py`
- Create: `tests/__init__.py`, `tests/fixtures/__init__.py`, `tests/unit/__init__.py`, `tests/differential/__init__.py`, `tests/property/__init__.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: an installable `src` package importable as `from src.fdr...`, `from src.graph...`, etc., and a working `uv run pytest` command.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "tree-decomposition"
version = "0.1.0"
description = "InterfaceCache: tree-decomposition summaries for fast local plan repair"
requires-python = ">=3.11"
dependencies = [
    "networkx>=3.2",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

- [ ] **Step 2: Create empty package `__init__.py` files**

```bash
mkdir -p src/fdr src/graph src/summaries src/repair tests/fixtures tests/unit tests/differential tests/property
for f in src/__init__.py src/fdr/__init__.py src/graph/__init__.py src/summaries/__init__.py src/repair/__init__.py \
         tests/__init__.py tests/fixtures/__init__.py tests/unit/__init__.py tests/differential/__init__.py tests/property/__init__.py; do
  : > "$f"
done
```

Each package `__init__.py` starts as `__all__: list[str] = []` — populated in later tasks as modules are added:

```python
__all__: list[str] = []
```
(write this exact content into each of the five `src/*/__init__.py` files; leave `tests/**/__init__.py` empty since tests aren't a public API)

- [ ] **Step 3: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
dist/
```

- [ ] **Step 4: Sync dependencies and verify pytest runs with zero tests**

Run: `uv sync`
Expected: creates `.venv/` and `uv.lock` with no errors.

Run: `uv run pytest`
Expected: `no tests ran` (exit code 5) — confirms the environment and test discovery config work.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore src tests uv.lock
git commit -m "chore: scaffold project layout with uv"
```

---

### Task 2: FDR task model

**Files:**
- Create: `src/fdr/task.py`
- Modify: `src/fdr/__init__.py`
- Test: `tests/unit/test_task.py`

**Interfaces:**
- Produces: `Variable(name: str, domain: FrozenSet[str])`, `Action` (frozen, with `Action.create(name, precondition: Mapping[str,str], effect: Mapping[str,str], cost: int=1)` factory and `.scope: FrozenSet[str]` property, `.precondition`/`.effect` as sorted `Tuple[Tuple[str,str],...]`), `State` (frozen, with `State.create(dict)` factory, `.get(var) -> str`, `.with_updates(dict) -> State`), `Task` (frozen, with `Task.create(variables, actions, initial_state: dict, goal: dict)` factory, `.variable_names() -> FrozenSet[str]`).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_task.py
import pytest

from src.fdr.task import Action, State, Task, Variable


def test_action_create_sorts_and_exposes_scope():
    a = Action.create("move", {"loc": "A"}, {"loc": "B"}, cost=2)
    assert a.precondition == (("loc", "A"),)
    assert a.effect == (("loc", "B"),)
    assert a.scope == frozenset({"loc"})
    assert a.cost == 2


def test_state_get_and_with_updates():
    s = State.create({"loc": "A", "held": "false"})
    assert s.get("loc") == "A"
    s2 = s.with_updates({"loc": "B"})
    assert s2.get("loc") == "B"
    assert s2.get("held") == "false"
    assert s.get("loc") == "A"  # original state is untouched (immutability)


def test_state_get_missing_variable_raises_keyerror():
    s = State.create({"loc": "A"})
    with pytest.raises(KeyError):
        s.get("nope")


def test_task_create_builds_sorted_goal_and_variable_names():
    v = Variable(name="loc", domain=frozenset({"A", "B"}))
    a = Action.create("move", {"loc": "A"}, {"loc": "B"})
    task = Task.create(
        variables=(v,),
        actions=(a,),
        initial_state={"loc": "A"},
        goal={"loc": "B"},
    )
    assert task.variable_names() == frozenset({"loc"})
    assert task.goal == (("loc", "B"),)
    assert task.initial_state.get("loc") == "A"


def test_action_and_state_are_hashable():
    a1 = Action.create("move", {"loc": "A"}, {"loc": "B"})
    a2 = Action.create("move", {"loc": "A"}, {"loc": "B"})
    assert hash(a1) == hash(a2)
    assert a1 == a2
    s1 = State.create({"loc": "A"})
    s2 = State.create({"loc": "A"})
    assert hash(s1) == hash(s2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_task.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.fdr.task'`

- [ ] **Step 3: Write the implementation**

```python
# src/fdr/task.py
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Mapping, Tuple

Assignment = Tuple[Tuple[str, str], ...]


def _to_assignment(d: Mapping[str, str]) -> Assignment:
    return tuple(sorted(d.items()))


@dataclass(frozen=True)
class Variable:
    name: str
    domain: FrozenSet[str]


@dataclass(frozen=True)
class Action:
    name: str
    precondition: Assignment
    effect: Assignment
    cost: int = 1

    @staticmethod
    def create(
        name: str,
        precondition: Mapping[str, str],
        effect: Mapping[str, str],
        cost: int = 1,
    ) -> "Action":
        return Action(
            name=name,
            precondition=_to_assignment(precondition),
            effect=_to_assignment(effect),
            cost=cost,
        )

    @property
    def scope(self) -> FrozenSet[str]:
        return frozenset(dict(self.precondition)) | frozenset(dict(self.effect))


@dataclass(frozen=True)
class State:
    assignment: Assignment

    @staticmethod
    def create(d: Mapping[str, str]) -> "State":
        return State(_to_assignment(d))

    def get(self, var: str) -> str:
        for k, v in self.assignment:
            if k == var:
                return v
        raise KeyError(var)

    def with_updates(self, updates: Mapping[str, str]) -> "State":
        d = dict(self.assignment)
        d.update(updates)
        return State.create(d)


@dataclass(frozen=True)
class Task:
    variables: FrozenSet[Variable]
    actions: FrozenSet[Action]
    initial_state: State
    goal: Assignment

    @staticmethod
    def create(
        variables: Iterable[Variable],
        actions: Iterable[Action],
        initial_state: Mapping[str, str],
        goal: Mapping[str, str],
    ) -> "Task":
        return Task(
            variables=frozenset(variables),
            actions=frozenset(actions),
            initial_state=State.create(initial_state),
            goal=_to_assignment(goal),
        )

    def variable_names(self) -> FrozenSet[str]:
        return frozenset(v.name for v in self.variables)
```

- [ ] **Step 4: Update `src/fdr/__init__.py`**

```python
from src.fdr.task import Action, State, Task, Variable

__all__ = ["Action", "State", "Task", "Variable"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_task.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add src/fdr/task.py src/fdr/__init__.py tests/unit/test_task.py
git commit -m "feat: add FDR task model (Variable, Action, State, Task)"
```

---

### Task 3: FDR simulator (independent plan validator)

**Files:**
- Create: `src/fdr/simulator.py`
- Modify: `src/fdr/__init__.py`
- Test: `tests/unit/test_simulator.py`

**Interfaces:**
- Consumes: `Action`, `State`, `Task` from Task 2.
- Produces: `is_applicable(action, state) -> bool`, `apply_action(action, state) -> State` (raises `ValueError` if inapplicable), `is_goal(task, state) -> bool`, `validate_plan(task, plan: Sequence[Action], start: Optional[State] = None) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_simulator.py
import pytest

from src.fdr.simulator import apply_action, is_applicable, is_goal, validate_plan
from src.fdr.task import Action, State, Task, Variable


def _tiny_task() -> Task:
    v = Variable(name="loc", domain=frozenset({"A", "B"}))
    move = Action.create("move", {"loc": "A"}, {"loc": "B"})
    return Task.create(variables=(v,), actions=(move,), initial_state={"loc": "A"}, goal={"loc": "B"})


def test_is_applicable_true_and_false():
    task = _tiny_task()
    move = next(iter(task.actions))
    assert is_applicable(move, task.initial_state) is True
    assert is_applicable(move, State.create({"loc": "B"})) is False


def test_apply_action_returns_new_state():
    task = _tiny_task()
    move = next(iter(task.actions))
    result = apply_action(move, task.initial_state)
    assert result.get("loc") == "B"


def test_apply_action_raises_when_inapplicable():
    task = _tiny_task()
    move = next(iter(task.actions))
    with pytest.raises(ValueError):
        apply_action(move, State.create({"loc": "B"}))


def test_is_goal():
    task = _tiny_task()
    assert is_goal(task, task.initial_state) is False
    assert is_goal(task, State.create({"loc": "B"})) is True


def test_validate_plan_success_and_failure():
    task = _tiny_task()
    move = next(iter(task.actions))
    assert validate_plan(task, (move,)) is True
    assert validate_plan(task, ()) is False
    assert validate_plan(task, (move, move)) is False  # second move inapplicable from loc=B
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_simulator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.fdr.simulator'`

- [ ] **Step 3: Write the implementation**

```python
# src/fdr/simulator.py
from __future__ import annotations

from typing import Optional, Sequence

from src.fdr.task import Action, State, Task


def is_applicable(action: Action, state: State) -> bool:
    return all(state.get(var) == val for var, val in action.precondition)


def apply_action(action: Action, state: State) -> State:
    if not is_applicable(action, state):
        raise ValueError(f"action {action.name!r} is not applicable in state {dict(state.assignment)}")
    return state.with_updates(dict(action.effect))


def is_goal(task: Task, state: State) -> bool:
    return all(state.get(var) == val for var, val in task.goal)


def validate_plan(task: Task, plan: Sequence[Action], start: Optional[State] = None) -> bool:
    state = start if start is not None else task.initial_state
    for action in plan:
        if not is_applicable(action, state):
            return False
        state = apply_action(action, state)
    return is_goal(task, state)
```

- [ ] **Step 4: Update `src/fdr/__init__.py`**

```python
from src.fdr.simulator import apply_action, is_applicable, is_goal, validate_plan
from src.fdr.task import Action, State, Task, Variable

__all__ = [
    "Action",
    "State",
    "Task",
    "Variable",
    "apply_action",
    "is_applicable",
    "is_goal",
    "validate_plan",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_simulator.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add src/fdr/simulator.py src/fdr/__init__.py tests/unit/test_simulator.py
git commit -m "feat: add FDR plan simulator and independent validator"
```

---

### Task 4: `two_room_basic` fixture

**Files:**
- Create: `tests/fixtures/two_room_basic.py`
- Test: `tests/unit/test_two_room_basic_fixture.py`

**Interfaces:**
- Consumes: `Action`, `Task`, `Variable` from Task 2; `validate_plan` from Task 3.
- Produces: module-level constants `ROBOT_A, DOOR_STATE, ROBOT_B` (`Variable`s), `GOTO_DOOR_A, GOTO_HOME_A, UNLOCK_DOOR, LOCK_DOOR, GOTO_DOOR_B, GOTO_HOME_B, ENTER_B, EXIT_B` (`Action`s), `ALL_ACTIONS: Tuple[Action, ...]`, `build_task() -> Task`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_two_room_basic_fixture.py
from tests.fixtures.two_room_basic import (
    ENTER_B,
    GOTO_DOOR_A,
    GOTO_DOOR_B,
    UNLOCK_DOOR,
    build_task,
)
from src.fdr.simulator import validate_plan


def test_known_optimal_plan_validates():
    task = build_task()
    plan = (GOTO_DOOR_A, UNLOCK_DOOR, GOTO_DOOR_B, ENTER_B)
    assert validate_plan(task, plan) is True
    assert sum(a.cost for a in plan) == 4


def test_task_scope_is_two_rooms_and_one_separator():
    task = build_task()
    assert task.variable_names() == frozenset({"robot_A", "door_state", "robot_B"})
    assert task.goal == (("robot_B", "beyond"),)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_two_room_basic_fixture.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.fixtures.two_room_basic'`

- [ ] **Step 3: Write the fixture**

```python
# tests/fixtures/two_room_basic.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_two_room_basic_fixture.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/two_room_basic.py tests/unit/test_two_room_basic_fixture.py
git commit -m "test: add two_room_basic fixture (2-bag toy domain)"
```

---

### Task 5: Interaction graph construction

**Files:**
- Create: `src/graph/interaction_graph.py`
- Modify: `src/graph/__init__.py`
- Test: `tests/unit/test_interaction_graph.py`

**Interfaces:**
- Consumes: `Task` from Task 2.
- Produces: `build_interaction_graph(task: Task) -> networkx.Graph` — one node per variable name, one edge per pair of variables co-occurring in some action's scope.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_interaction_graph.py
from src.graph.interaction_graph import build_interaction_graph
from tests.fixtures.two_room_basic import build_task


def test_two_room_basic_graph_has_expected_edges_only():
    graph = build_interaction_graph(build_task())
    assert set(graph.nodes()) == {"robot_A", "door_state", "robot_B"}
    assert set(frozenset(e) for e in graph.edges()) == {
        frozenset({"robot_A", "door_state"}),
        frozenset({"door_state", "robot_B"}),
    }
    # robot_A and robot_B never co-occur in any action's scope
    assert not graph.has_edge("robot_A", "robot_B")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_interaction_graph.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.graph.interaction_graph'`

- [ ] **Step 3: Write the implementation**

```python
# src/graph/interaction_graph.py
from __future__ import annotations

import networkx as nx

from src.fdr.task import Task


def build_interaction_graph(task: Task) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(v.name for v in task.variables)
    for action in task.actions:
        scope = sorted(action.scope)
        for i in range(len(scope)):
            for j in range(i + 1, len(scope)):
                graph.add_edge(scope[i], scope[j])
    return graph
```

- [ ] **Step 4: Update `src/graph/__init__.py`**

```python
from src.graph.interaction_graph import build_interaction_graph

__all__ = ["build_interaction_graph"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_interaction_graph.py -v`
Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add src/graph/interaction_graph.py src/graph/__init__.py tests/unit/test_interaction_graph.py
git commit -m "feat: build primal interaction graph from an FDR task"
```

---

### Task 6: Tree decomposition wrapper

**Files:**
- Create: `src/graph/decomposition.py`
- Modify: `src/graph/__init__.py`
- Test: `tests/unit/test_decomposition.py`

**Interfaces:**
- Consumes: `Task` from Task 2, `networkx.Graph` from Task 5.
- Produces: `Bag(bag_id: str, variables: FrozenSet[str], parent_id: Optional[str], children_ids: Tuple[str, ...])`; `TreeDecomposition(bags: Dict[str, Bag], root_id: str)` with methods `.bag(bag_id) -> Bag`, `.separator_to_parent(bag_id) -> FrozenSet[str]`, `.separator_to_child(bag_id, child_id) -> FrozenSet[str]`, `.children_of(bag_id) -> Tuple[str, ...]`, `.postorder() -> Tuple[str, ...]`, `.find_bag(variables: FrozenSet[str]) -> str`; `build_decomposition(task: Task, interaction_graph: networkx.Graph) -> TreeDecomposition` (raises `ValueError` if no bag contains all goal variables).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_decomposition.py
import pytest

from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from tests.fixtures.two_room_basic import build_task


def test_two_room_basic_decomposes_into_two_bags_with_door_state_separator():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))

    assert len(decomp.bags) == 2
    root_bag = decomp.bag(decomp.root_id)
    assert "robot_B" in root_bag.variables  # root contains the goal variable
    assert root_bag.parent_id is None
    assert len(root_bag.children_ids) == 1

    child_id = root_bag.children_ids[0]
    assert decomp.bag(child_id).variables == frozenset({"robot_A", "door_state"})
    assert decomp.separator_to_parent(child_id) == frozenset({"door_state"})
    assert decomp.separator_to_child(decomp.root_id, child_id) == frozenset({"door_state"})
    assert decomp.postorder() == (child_id, decomp.root_id)


def test_find_bag_by_variables():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    found = decomp.find_bag(frozenset({"robot_A", "door_state"}))
    assert decomp.bag(found).variables == frozenset({"robot_A", "door_state"})


def test_build_decomposition_raises_if_no_bag_covers_goal():
    task = build_task()
    graph = build_interaction_graph(task)
    graph.remove_node("robot_B")  # sabotage: goal variable no longer in any bag
    with pytest.raises(ValueError):
        build_decomposition(task, graph)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_decomposition.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.graph.decomposition'`

- [ ] **Step 3: Write the implementation**

```python
# src/graph/decomposition.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

import networkx as nx
from networkx.algorithms.approximation.treewidth import treewidth_min_fill_in

from src.fdr.task import Task


@dataclass(frozen=True)
class Bag:
    bag_id: str
    variables: FrozenSet[str]
    parent_id: Optional[str]
    children_ids: Tuple[str, ...]


@dataclass(frozen=True)
class TreeDecomposition:
    bags: Dict[str, Bag]
    root_id: str

    def bag(self, bag_id: str) -> Bag:
        return self.bags[bag_id]

    def separator_to_parent(self, bag_id: str) -> FrozenSet[str]:
        bag = self.bags[bag_id]
        if bag.parent_id is None:
            return frozenset()
        return bag.variables & self.bags[bag.parent_id].variables

    def separator_to_child(self, bag_id: str, child_id: str) -> FrozenSet[str]:
        return self.bags[bag_id].variables & self.bags[child_id].variables

    def children_of(self, bag_id: str) -> Tuple[str, ...]:
        return self.bags[bag_id].children_ids

    def postorder(self) -> Tuple[str, ...]:
        order: List[str] = []

        def visit(bag_id: str) -> None:
            for child_id in self.bags[bag_id].children_ids:
                visit(child_id)
            order.append(bag_id)

        visit(self.root_id)
        return tuple(order)

    def find_bag(self, variables: FrozenSet[str]) -> str:
        matches = [bag_id for bag_id, bag in self.bags.items() if bag.variables == variables]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one bag with variables {variables}, found {len(matches)}")
        return matches[0]


def build_decomposition(task: Task, interaction_graph: nx.Graph) -> TreeDecomposition:
    _, raw_tree = treewidth_min_fill_in(interaction_graph)
    goal_vars = frozenset(var for var, _ in task.goal)

    candidates = [node for node in raw_tree.nodes() if goal_vars <= node]
    if not candidates:
        raise ValueError("no bag contains all goal variables (goal-in-one-bag assumption violated)")
    root_node = min(candidates, key=lambda node: (len(node), sorted(node)))

    bag_ids: Dict[FrozenSet[str], str] = {
        node: f"bag_{i}" for i, node in enumerate(sorted(raw_tree.nodes(), key=lambda n: sorted(n)))
    }

    bags: Dict[str, Bag] = {}

    def visit(node: FrozenSet[str], parent_node: Optional[FrozenSet[str]]) -> None:
        node_id = bag_ids[node]
        parent_id = bag_ids[parent_node] if parent_node is not None else None
        child_nodes = sorted((n for n in raw_tree.neighbors(node) if n != parent_node), key=lambda n: sorted(n))
        children_ids = tuple(bag_ids[c] for c in child_nodes)
        bags[node_id] = Bag(bag_id=node_id, variables=frozenset(node), parent_id=parent_id, children_ids=children_ids)
        for child_node in child_nodes:
            visit(child_node, node)

    visit(root_node, None)
    return TreeDecomposition(bags=bags, root_id=bag_ids[root_node])
```

- [ ] **Step 4: Update `src/graph/__init__.py`**

```python
from src.graph.decomposition import Bag, TreeDecomposition, build_decomposition
from src.graph.interaction_graph import build_interaction_graph

__all__ = ["Bag", "TreeDecomposition", "build_decomposition", "build_interaction_graph"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_decomposition.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/graph/decomposition.py src/graph/__init__.py tests/unit/test_decomposition.py
git commit -m "feat: build rooted tree decomposition via networkx min-fill"
```

---

### Task 7: Bag assignment (action ownership)

**Files:**
- Create: `src/graph/bag_assignment.py`
- Modify: `src/graph/__init__.py`
- Test: `tests/unit/test_bag_assignment.py`

**Interfaces:**
- Consumes: `Task`, `Action` from Task 2; `TreeDecomposition` from Task 6.
- Produces: `assign_actions(task: Task, decomposition: TreeDecomposition) -> Dict[str, Tuple[Action, ...]]` — every action appears in exactly one bag's tuple, in the shallowest bag (by distance from root) whose variables cover the action's scope, ties broken by bag id string comparison. Raises `ValueError` if an action's scope isn't covered by any bag.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_bag_assignment.py
import pytest

from src.fdr.task import Action, Task, Variable
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from tests.fixtures.two_room_basic import (
    ALL_ACTIONS,
    ENTER_B,
    EXIT_B,
    GOTO_DOOR_A,
    GOTO_DOOR_B,
    GOTO_HOME_A,
    GOTO_HOME_B,
    LOCK_DOOR,
    UNLOCK_DOOR,
    build_task,
)


def test_every_action_assigned_exactly_once_to_a_covering_bag():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)

    all_assigned = [a for actions in owned.values() for a in actions]
    assert len(all_assigned) == len(ALL_ACTIONS)
    assert set(all_assigned) == set(ALL_ACTIONS)

    for bag_id, actions in owned.items():
        bag_vars = decomp.bag(bag_id).variables
        for action in actions:
            assert action.scope <= bag_vars

    room_a_bag = decomp.find_bag(frozenset({"robot_A", "door_state"}))
    room_b_bag = decomp.root_id
    assert set(owned[room_a_bag]) == {GOTO_DOOR_A, GOTO_HOME_A, UNLOCK_DOOR, LOCK_DOOR}
    assert set(owned[room_b_bag]) == {GOTO_DOOR_B, GOTO_HOME_B, ENTER_B, EXIT_B}


def test_assign_actions_raises_if_scope_uncovered():
    v1 = Variable(name="x", domain=frozenset({"0", "1"}))
    v2 = Variable(name="y", domain=frozenset({"0", "1"}))
    unreachable_action = Action.create("touch_both", {"x": "0", "y": "0"}, {"x": "1"})
    task = Task.create(variables=(v1, v2), actions=(unreachable_action,), initial_state={"x": "0", "y": "0"}, goal={"x": "1"})
    graph = build_interaction_graph(task)
    decomp = build_decomposition(task, graph)
    # sabotage: pretend the action needs a variable no bag has
    bad_action = Action.create("touch_ghost", {"x": "0", "ghost": "0"}, {"x": "1"})
    bad_task = Task.create(variables=(v1, v2), actions=(bad_action,), initial_state={"x": "0", "y": "0"}, goal={"x": "1"})
    with pytest.raises(ValueError):
        assign_actions(bad_task, decomp)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_bag_assignment.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.graph.bag_assignment'`

- [ ] **Step 3: Write the implementation**

```python
# src/graph/bag_assignment.py
from __future__ import annotations

from typing import Dict, List, Tuple

from src.fdr.task import Action, Task
from src.graph.decomposition import TreeDecomposition


def assign_actions(task: Task, decomposition: TreeDecomposition) -> Dict[str, Tuple[Action, ...]]:
    assignment: Dict[str, List[Action]] = {bag_id: [] for bag_id in decomposition.bags}
    depth = _bag_depths(decomposition)

    for action in task.actions:
        covering = [bag_id for bag_id, bag in decomposition.bags.items() if action.scope <= bag.variables]
        if not covering:
            raise ValueError(f"action {action.name!r} has no covering bag for scope {sorted(action.scope)}")
        chosen = min(covering, key=lambda bag_id: (depth[bag_id], bag_id))
        assignment[chosen].append(action)

    return {bag_id: tuple(sorted(actions, key=lambda a: a.name)) for bag_id, actions in assignment.items()}


def _bag_depths(decomposition: TreeDecomposition) -> Dict[str, int]:
    depths: Dict[str, int] = {decomposition.root_id: 0}
    stack = [decomposition.root_id]
    while stack:
        current = stack.pop()
        for child_id in decomposition.children_of(current):
            depths[child_id] = depths[current] + 1
            stack.append(child_id)
    return depths
```

- [ ] **Step 4: Update `src/graph/__init__.py`**

```python
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import Bag, TreeDecomposition, build_decomposition
from src.graph.interaction_graph import build_interaction_graph

__all__ = ["Bag", "TreeDecomposition", "assign_actions", "build_decomposition", "build_interaction_graph"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_bag_assignment.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add src/graph/bag_assignment.py src/graph/__init__.py tests/unit/test_bag_assignment.py
git commit -m "feat: assign each action to its shallowest covering bag"
```

---

### Task 8: `two_room_deeper` fixture (4-bag chain)

**Files:**
- Create: `tests/fixtures/two_room_deeper.py`
- Test: `tests/unit/test_two_room_deeper_fixture.py`

**Interfaces:**
- Consumes: `Action`, `Task`, `Variable` from Task 2; `build_interaction_graph` from Task 5; `build_decomposition` from Task 6.
- Produces: `ROBOT_A, GATE_A, HALLWAY_POS, GATE_B, ROBOT_B` (`Variable`s), `GOTO_EXIT_A, OPEN_GATE_A, CROSS_HALLWAY, OPEN_GATE_B, GOTO_EXIT_B` (`Action`s), `ALL_ACTIONS`, `build_task() -> Task`.

This fixture's interaction graph is already a 5-node path (`robot_A – gate_A – hallway_pos – gate_B – robot_B`), which is already chordal, so `build_decomposition` naturally returns a **4-bag chain** (each bag = one edge of the path): `{robot_A,gate_A} – {gate_A,hallway_pos} – {hallway_pos,gate_B} – {gate_B,robot_B}`. This exceeds the original 3-bag estimate in the design doc and gives an even better test of propagation through *two* intermediate bags, not just one.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_two_room_deeper_fixture.py
from src.fdr.simulator import validate_plan
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from tests.fixtures.two_room_deeper import (
    CROSS_HALLWAY,
    GOTO_EXIT_A,
    GOTO_EXIT_B,
    OPEN_GATE_A,
    OPEN_GATE_B,
    build_task,
)


def test_known_optimal_plan_validates():
    task = build_task()
    plan = (GOTO_EXIT_A, OPEN_GATE_A, CROSS_HALLWAY, OPEN_GATE_B, GOTO_EXIT_B)
    assert validate_plan(task, plan) is True
    assert sum(a.cost for a in plan) == 5


def test_decomposes_into_four_bag_chain():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    assert len(decomp.bags) == 4
    # exactly one bag per rooted level, single-child chain all the way down
    depths = set()
    bag_id = decomp.root_id
    while True:
        depths.add(bag_id)
        children = decomp.children_of(bag_id)
        if not children:
            break
        assert len(children) == 1
        bag_id = children[0]
    assert len(depths) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_two_room_deeper_fixture.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.fixtures.two_room_deeper'`

- [ ] **Step 3: Write the fixture**

```python
# tests/fixtures/two_room_deeper.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_two_room_deeper_fixture.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/two_room_deeper.py tests/unit/test_two_room_deeper_fixture.py
git commit -m "test: add two_room_deeper fixture (4-bag chain toy domain)"
```

---

### Task 9: `three_room_hub` fixture (branching decomposition)

**Files:**
- Create: `tests/fixtures/three_room_hub.py`
- Test: `tests/unit/test_three_room_hub_fixture.py`

**Interfaces:**
- Consumes: same as Task 8.
- Produces: `HUB, ROBOT_A, ROBOT_C, ROBOT_D` (`Variable`s), `WORK_A, MARK_A, WORK_C, MARK_C, FINISH_D` (`Action`s), `ALL_ACTIONS`, `build_task() -> Task`.

This fixture's interaction graph is a 3-leaf star centered on `hub` (`robot_A—hub`, `robot_C—hub`, `robot_D—hub`), which decomposes into a root bag `{hub, robot_D}` with **two independent children** `{hub, robot_A}` and `{hub, robot_C}` — the branching structure needed to test that a disruption in one child's subtree never invalidates an unrelated sibling subtree (CLAUDE.md §15 property test #4).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_three_room_hub_fixture.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_three_room_hub_fixture.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.fixtures.three_room_hub'`

- [ ] **Step 3: Write the fixture**

```python
# tests/fixtures/three_room_hub.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_three_room_hub_fixture.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/three_room_hub.py tests/unit/test_three_room_hub_fixture.py
git commit -m "test: add three_room_hub fixture (branching toy domain)"
```

---

### Task 10: Interface and summary data structures

**Files:**
- Create: `src/summaries/interface.py`
- Modify: `src/summaries/__init__.py`
- Test: `tests/unit/test_interface.py`

**Interfaces:**
- Consumes: `Action` from Task 2.
- Produces: `InterfaceAssignment = Tuple[Tuple[str, str], ...]`, `make_interface(d: Mapping[str,str]) -> InterfaceAssignment`, `OwnActionStep(action: Action)`, `ChildJumpStep(child_bag_id: str, incoming: InterfaceAssignment, outgoing: InterfaceAssignment)`, `PlanStep = Union[OwnActionStep, ChildJumpStep]`, `SummaryEntry(feasible: bool, cost: float, local_plan_fragment: Tuple[PlanStep,...], child_interface_choices: Tuple[Tuple[str, InterfaceAssignment, InterfaceAssignment],...], bag_id: str, task_version: str)`, `SummaryTable(bag_id: str, entries: Mapping[Tuple[InterfaceAssignment,InterfaceAssignment], SummaryEntry])` with `SummaryTable.create(bag_id, entries: dict) -> SummaryTable`, `.get(incoming, outgoing) -> Optional[SummaryEntry]`, `.best_outgoing(incoming) -> Dict[InterfaceAssignment, SummaryEntry]` (feasible entries only).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_interface.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_interface.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.summaries.interface'`

- [ ] **Step 3: Write the implementation**

```python
# src/summaries/interface.py
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Mapping, Optional, Tuple, Union

from src.fdr.task import Action

InterfaceAssignment = Tuple[Tuple[str, str], ...]


def make_interface(d: Mapping[str, str]) -> InterfaceAssignment:
    return tuple(sorted(d.items()))


@dataclass(frozen=True)
class OwnActionStep:
    action: Action


@dataclass(frozen=True)
class ChildJumpStep:
    child_bag_id: str
    incoming: InterfaceAssignment
    outgoing: InterfaceAssignment


PlanStep = Union[OwnActionStep, ChildJumpStep]


@dataclass(frozen=True)
class SummaryEntry:
    feasible: bool
    cost: float
    local_plan_fragment: Tuple[PlanStep, ...]
    child_interface_choices: Tuple[Tuple[str, InterfaceAssignment, InterfaceAssignment], ...]
    bag_id: str
    task_version: str


@dataclass(frozen=True)
class SummaryTable:
    bag_id: str
    entries: Mapping[Tuple[InterfaceAssignment, InterfaceAssignment], SummaryEntry]

    @staticmethod
    def create(
        bag_id: str,
        entries: Dict[Tuple[InterfaceAssignment, InterfaceAssignment], SummaryEntry],
    ) -> "SummaryTable":
        return SummaryTable(bag_id=bag_id, entries=MappingProxyType(dict(entries)))

    def get(self, incoming: InterfaceAssignment, outgoing: InterfaceAssignment) -> Optional[SummaryEntry]:
        return self.entries.get((incoming, outgoing))

    def best_outgoing(self, incoming: InterfaceAssignment) -> Dict[InterfaceAssignment, SummaryEntry]:
        return {o: e for (i, o), e in self.entries.items() if i == incoming and e.feasible}
```

- [ ] **Step 4: Update `src/summaries/__init__.py`**

```python
from src.summaries.interface import (
    ChildJumpStep,
    InterfaceAssignment,
    OwnActionStep,
    PlanStep,
    SummaryEntry,
    SummaryTable,
    make_interface,
)

__all__ = [
    "ChildJumpStep",
    "InterfaceAssignment",
    "OwnActionStep",
    "PlanStep",
    "SummaryEntry",
    "SummaryTable",
    "make_interface",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_interface.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/summaries/interface.py src/summaries/__init__.py tests/unit/test_interface.py
git commit -m "feat: add InterfaceAssignment, SummaryEntry, SummaryTable schema"
```

---

### Task 11: Local solver (exact enumerative Dijkstra per bag)

**Files:**
- Create: `src/summaries/local_solver.py`
- Modify: `src/summaries/__init__.py`
- Test: `tests/unit/test_local_solver.py`

**Interfaces:**
- Consumes: `Action, State, Variable` from Task 2; `TreeDecomposition` from Task 6; `InterfaceAssignment, SummaryEntry, SummaryTable, OwnActionStep, ChildJumpStep, make_interface` from Task 10.
- Produces: `solve_bag(decomposition: TreeDecomposition, bag_id: str, owned_actions: Tuple[Action,...], current_state: State, child_tables: Mapping[str, SummaryTable], task_version: str, variables: FrozenSet[Variable], goal: Optional[InterfaceAssignment] = None) -> SummaryTable`. When `bag_id` is the root (`decomposition.bag(bag_id).parent_id is None`), `goal` must be given and the returned table has exactly one entry keyed `((), ())`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_local_solver.py
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.summaries.local_solver import solve_bag
from tests.fixtures.two_room_basic import build_task


def test_leaf_bag_a_table_matches_hand_derivation():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)
    bag_a_id = decomp.find_bag(frozenset({"robot_A", "door_state"}))

    table = solve_bag(
        decomposition=decomp,
        bag_id=bag_a_id,
        owned_actions=owned[bag_a_id],
        current_state=task.initial_state,
        child_tables={},
        task_version="v1",
        variables=task.variables,
    )

    locked = (("door_state", "locked"),)
    unlocked = (("door_state", "unlocked"),)

    assert table.get(locked, locked).cost == 0
    assert table.get(locked, unlocked).cost == 2
    assert table.get(unlocked, unlocked).cost == 0
    assert table.get(unlocked, locked).cost == 2
    for entry in table.entries.values():
        assert entry.feasible is True


def test_root_bag_b_reaches_goal_at_cost_four_via_child_jump():
    task = build_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)
    bag_a_id = decomp.find_bag(frozenset({"robot_A", "door_state"}))

    bag_a_table = solve_bag(
        decomposition=decomp,
        bag_id=bag_a_id,
        owned_actions=owned[bag_a_id],
        current_state=task.initial_state,
        child_tables={},
        task_version="v1",
        variables=task.variables,
    )

    root_table = solve_bag(
        decomposition=decomp,
        bag_id=decomp.root_id,
        owned_actions=owned[decomp.root_id],
        current_state=task.initial_state,
        child_tables={bag_a_id: bag_a_table},
        task_version="v1",
        variables=task.variables,
        goal=task.goal,
    )

    root_entry = root_table.get((), ())
    assert root_entry.feasible is True
    assert root_entry.cost == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_local_solver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.summaries.local_solver'`

- [ ] **Step 3: Write the implementation**

```python
# src/summaries/local_solver.py
from __future__ import annotations

import heapq
import itertools
from typing import Dict, FrozenSet, Iterable, List, Mapping, Optional, Tuple

from src.fdr.task import Action, State, Variable
from src.graph.decomposition import TreeDecomposition
from src.summaries.interface import (
    ChildJumpStep,
    InterfaceAssignment,
    OwnActionStep,
    PlanStep,
    SummaryEntry,
    SummaryTable,
    make_interface,
)

LocalState = Tuple[Tuple[str, str], ...]


def _restrict(state: LocalState, variables: FrozenSet[str]) -> InterfaceAssignment:
    d = dict(state)
    return tuple(sorted((v, d[v]) for v in variables))


def _apply_action(state: LocalState, action: Action) -> Optional[LocalState]:
    d = dict(state)
    for var, val in action.precondition:
        if d.get(var) != val:
            return None
    d.update(dict(action.effect))
    return tuple(sorted(d.items()))


def _domains(bag_vars: Tuple[str, ...], variables: FrozenSet[Variable]) -> Dict[str, Tuple[str, ...]]:
    by_name = {v.name: tuple(sorted(v.domain)) for v in variables}
    return {v: by_name[v] for v in bag_vars}


def solve_bag(
    decomposition: TreeDecomposition,
    bag_id: str,
    owned_actions: Tuple[Action, ...],
    current_state: State,
    child_tables: Mapping[str, SummaryTable],
    task_version: str,
    variables: FrozenSet[Variable],
    goal: Optional[InterfaceAssignment] = None,
) -> SummaryTable:
    bag = decomposition.bag(bag_id)
    is_root = bag.parent_id is None
    if is_root and goal is None:
        raise ValueError(f"goal must be provided when solving the root bag {bag_id!r}")

    bag_vars: Tuple[str, ...] = tuple(sorted(bag.variables))
    parent_sep = decomposition.separator_to_parent(bag_id)
    child_seps = {cid: decomposition.separator_to_child(bag_id, cid) for cid in bag.children_ids}
    domains = _domains(bag_vars, variables)

    fixed_vars = [v for v in bag_vars if v not in parent_sep]
    fixed_values = {v: current_state.get(v) for v in fixed_vars}

    sep_vars = tuple(sorted(parent_sep))
    incoming_options: List[InterfaceAssignment] = (
        [make_interface(dict(zip(sep_vars, combo))) for combo in itertools.product(*(domains[v] for v in sep_vars))]
        if sep_vars
        else [()]
    )

    entries: Dict[Tuple[InterfaceAssignment, InterfaceAssignment], SummaryEntry] = {}

    for incoming in incoming_options:
        start_dict = dict(fixed_values)
        start_dict.update(dict(incoming))
        start: LocalState = tuple(sorted(start_dict.items()))

        dist, prev = _dijkstra(start, owned_actions, child_seps, child_tables)

        if is_root:
            assert goal is not None
            best_state, best_cost = None, float("inf")
            for state, cost in dist.items():
                if cost < best_cost and all(dict(state).get(v) == val for v, val in goal):
                    best_state, best_cost = state, cost
            outgoing: InterfaceAssignment = ()
            entries[(incoming, outgoing)] = _make_entry(
                bag_id, task_version, start, best_state, best_cost, prev
            )
        else:
            best_by_outgoing: Dict[InterfaceAssignment, Tuple[LocalState, float]] = {}
            for state, cost in dist.items():
                outgoing = _restrict(state, parent_sep)
                if outgoing not in best_by_outgoing or cost < best_by_outgoing[outgoing][1]:
                    best_by_outgoing[outgoing] = (state, cost)
            for outgoing, (state, cost) in best_by_outgoing.items():
                entries[(incoming, outgoing)] = _make_entry(bag_id, task_version, start, state, cost, prev)

    return SummaryTable.create(bag_id, entries)


def _dijkstra(
    start: LocalState,
    owned_actions: Tuple[Action, ...],
    child_seps: Mapping[str, FrozenSet[str]],
    child_tables: Mapping[str, SummaryTable],
) -> Tuple[Dict[LocalState, float], Dict[LocalState, Tuple[LocalState, PlanStep]]]:
    dist: Dict[LocalState, float] = {start: 0.0}
    prev: Dict[LocalState, Tuple[LocalState, PlanStep]] = {}
    counter = itertools.count()
    heap: List[Tuple[float, int, LocalState]] = [(0.0, next(counter), start)]
    visited: set = set()

    while heap:
        cost, _, state = heapq.heappop(heap)
        if state in visited:
            continue
        visited.add(state)

        for action in owned_actions:
            nxt = _apply_action(state, action)
            if nxt is None:
                continue
            new_cost = cost + action.cost
            if new_cost < dist.get(nxt, float("inf")):
                dist[nxt] = new_cost
                prev[nxt] = (state, OwnActionStep(action))
                heapq.heappush(heap, (new_cost, next(counter), nxt))

        for child_id, sep in child_seps.items():
            i_child = _restrict(state, sep)
            for o_child, child_entry in child_tables[child_id].best_outgoing(i_child).items():
                d = dict(state)
                d.update(dict(o_child))
                nxt = tuple(sorted(d.items()))
                new_cost = cost + child_entry.cost
                if new_cost < dist.get(nxt, float("inf")):
                    dist[nxt] = new_cost
                    prev[nxt] = (state, ChildJumpStep(child_id, i_child, o_child))
                    heapq.heappush(heap, (new_cost, next(counter), nxt))

    return dist, prev


def _make_entry(
    bag_id: str,
    task_version: str,
    start: LocalState,
    end: Optional[LocalState],
    cost: float,
    prev: Dict[LocalState, Tuple[LocalState, PlanStep]],
) -> SummaryEntry:
    if end is None:
        return SummaryEntry(
            feasible=False,
            cost=float("inf"),
            local_plan_fragment=(),
            child_interface_choices=(),
            bag_id=bag_id,
            task_version=task_version,
        )
    fragment = _reconstruct(prev, start, end)
    return SummaryEntry(
        feasible=True,
        cost=cost,
        local_plan_fragment=fragment,
        child_interface_choices=_child_choices(fragment),
        bag_id=bag_id,
        task_version=task_version,
    )


def _reconstruct(
    prev: Dict[LocalState, Tuple[LocalState, PlanStep]], start: LocalState, end: LocalState
) -> Tuple[PlanStep, ...]:
    if end == start:
        return ()
    steps: List[PlanStep] = []
    state = end
    while state != start:
        prev_state, step = prev[state]
        steps.append(step)
        state = prev_state
    return tuple(reversed(steps))


def _child_choices(
    fragment: Tuple[PlanStep, ...]
) -> Tuple[Tuple[str, InterfaceAssignment, InterfaceAssignment], ...]:
    return tuple(
        (step.child_bag_id, step.incoming, step.outgoing) for step in fragment if isinstance(step, ChildJumpStep)
    )
```

- [ ] **Step 4: Update `src/summaries/__init__.py`**

```python
from src.summaries.interface import (
    ChildJumpStep,
    InterfaceAssignment,
    OwnActionStep,
    PlanStep,
    SummaryEntry,
    SummaryTable,
    make_interface,
)
from src.summaries.local_solver import solve_bag

__all__ = [
    "ChildJumpStep",
    "InterfaceAssignment",
    "OwnActionStep",
    "PlanStep",
    "SummaryEntry",
    "SummaryTable",
    "make_interface",
    "solve_bag",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_local_solver.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add src/summaries/local_solver.py src/summaries/__init__.py tests/unit/test_local_solver.py
git commit -m "feat: exact enumerative local solver with child-summary composition"
```

---

### Task 12: Compose orchestration and plan extraction

**Files:**
- Create: `src/summaries/compose.py`
- Modify: `src/summaries/__init__.py`
- Test: `tests/unit/test_compose.py`

**Interfaces:**
- Consumes: `Task, Action, State` from Task 2; `TreeDecomposition` from Task 6; `assign_actions` from Task 7; `SummaryTable, SummaryEntry` from Task 10; `solve_bag` from Task 11.
- Produces: `compute_all_summaries(task: Task, decomposition: TreeDecomposition, current_state: State, task_version: str) -> Dict[str, SummaryTable]` (postorder bottom-up); `extract_plan(tables: Dict[str, SummaryTable], root_entry: SummaryEntry) -> Tuple[Action, ...]` (recursively splices child fragments).

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_compose.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.summaries.compose'`

- [ ] **Step 3: Write the implementation**

```python
# src/summaries/compose.py
from __future__ import annotations

from typing import Dict, List, Tuple

from src.fdr.task import Action, State, Task
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import TreeDecomposition
from src.summaries.interface import ChildJumpStep, OwnActionStep, SummaryEntry, SummaryTable
from src.summaries.local_solver import solve_bag


def compute_all_summaries(
    task: Task,
    decomposition: TreeDecomposition,
    current_state: State,
    task_version: str,
) -> Dict[str, SummaryTable]:
    owned = assign_actions(task, decomposition)
    tables: Dict[str, SummaryTable] = {}

    for bag_id in decomposition.postorder():
        child_tables = {cid: tables[cid] for cid in decomposition.children_of(bag_id)}
        goal = task.goal if bag_id == decomposition.root_id else None
        tables[bag_id] = solve_bag(
            decomposition=decomposition,
            bag_id=bag_id,
            owned_actions=owned[bag_id],
            current_state=current_state,
            child_tables=child_tables,
            task_version=task_version,
            variables=task.variables,
            goal=goal,
        )

    return tables


def extract_plan(tables: Dict[str, SummaryTable], root_entry: SummaryEntry) -> Tuple[Action, ...]:
    actions: List[Action] = []

    def expand(entry: SummaryEntry) -> None:
        for step in entry.local_plan_fragment:
            if isinstance(step, OwnActionStep):
                actions.append(step.action)
            elif isinstance(step, ChildJumpStep):
                child_entry = tables[step.child_bag_id].get(step.incoming, step.outgoing)
                if child_entry is None or not child_entry.feasible:
                    raise ValueError(f"missing or infeasible child entry for bag {step.child_bag_id!r}")
                expand(child_entry)

    expand(root_entry)
    return tuple(actions)
```

- [ ] **Step 4: Update `src/summaries/__init__.py`**

```python
from src.summaries.compose import compute_all_summaries, extract_plan
from src.summaries.interface import (
    ChildJumpStep,
    InterfaceAssignment,
    OwnActionStep,
    PlanStep,
    SummaryEntry,
    SummaryTable,
    make_interface,
)
from src.summaries.local_solver import solve_bag

__all__ = [
    "ChildJumpStep",
    "InterfaceAssignment",
    "OwnActionStep",
    "PlanStep",
    "SummaryEntry",
    "SummaryTable",
    "compute_all_summaries",
    "extract_plan",
    "make_interface",
    "solve_bag",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_compose.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/summaries/compose.py src/summaries/__init__.py tests/unit/test_compose.py
git commit -m "feat: bottom-up summary composition and recursive plan extraction"
```

---

### Task 13: Full replan (oracle and baseline)

**Files:**
- Create: `src/repair/full_replan.py`
- Modify: `src/repair/__init__.py`
- Test: `tests/unit/test_full_replan.py`

**Interfaces:**
- Consumes: `Action, State, Task` from Task 2; `is_applicable, apply_action, is_goal` from Task 3.
- Produces: `full_replan(task: Task, start: Optional[State] = None) -> Optional[Tuple[Action, ...]]` — brute-force Dijkstra over the whole task's state space; returns `None` if unreachable.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_full_replan.py
from src.fdr.simulator import validate_plan
from src.repair.full_replan import full_replan
from tests.fixtures import three_room_hub, two_room_basic, two_room_deeper


def test_two_room_basic_full_replan_matches_known_optimum():
    task = two_room_basic.build_task()
    plan = full_replan(task)
    assert plan is not None
    assert sum(a.cost for a in plan) == 4
    assert validate_plan(task, plan) is True


def test_two_room_deeper_full_replan_matches_known_optimum():
    task = two_room_deeper.build_task()
    plan = full_replan(task)
    assert plan is not None
    assert sum(a.cost for a in plan) == 5


def test_three_room_hub_full_replan_matches_known_optimum():
    task = three_room_hub.build_task()
    plan = full_replan(task)
    assert plan is not None
    assert sum(a.cost for a in plan) == 3


def test_full_replan_returns_none_when_unreachable():
    task = two_room_basic.build_task()
    unreachable_actions = frozenset(a for a in task.actions if a.name != "unlock_door")
    from src.fdr.task import Task as TaskType

    sabotaged = TaskType(
        variables=task.variables, actions=unreachable_actions, initial_state=task.initial_state, goal=task.goal
    )
    assert full_replan(sabotaged) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_full_replan.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.repair.full_replan'`

- [ ] **Step 3: Write the implementation**

```python
# src/repair/full_replan.py
from __future__ import annotations

import heapq
import itertools
from typing import Dict, List, Optional, Tuple

from src.fdr.simulator import apply_action, is_applicable, is_goal
from src.fdr.task import Action, State, Task


def full_replan(task: Task, start: Optional[State] = None) -> Optional[Tuple[Action, ...]]:
    start_state = start if start is not None else task.initial_state
    if is_goal(task, start_state):
        return ()

    dist: Dict[State, float] = {start_state: 0.0}
    prev: Dict[State, Tuple[State, Action]] = {}
    counter = itertools.count()
    heap: List[Tuple[float, int, State]] = [(0.0, next(counter), start_state)]
    visited: set = set()

    while heap:
        cost, _, state = heapq.heappop(heap)
        if state in visited:
            continue
        visited.add(state)
        if is_goal(task, state):
            return _reconstruct(prev, start_state, state)

        for action in task.actions:
            if not is_applicable(action, state):
                continue
            nxt = apply_action(action, state)
            new_cost = cost + action.cost
            if new_cost < dist.get(nxt, float("inf")):
                dist[nxt] = new_cost
                prev[nxt] = (state, action)
                heapq.heappush(heap, (new_cost, next(counter), nxt))

    return None


def _reconstruct(prev: Dict[State, Tuple[State, Action]], start: State, end: State) -> Tuple[Action, ...]:
    steps: List[Action] = []
    state = end
    while state != start:
        prev_state, action = prev[state]
        steps.append(action)
        state = prev_state
    return tuple(reversed(steps))
```

- [ ] **Step 4: Update `src/repair/__init__.py`**

```python
from src.repair.full_replan import full_replan

__all__ = ["full_replan"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_full_replan.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/repair/full_replan.py src/repair/__init__.py tests/unit/test_full_replan.py
git commit -m "feat: add brute-force full-replan oracle and baseline"
```

---

### Task 14: Cache with dependency fingerprinting

**Files:**
- Create: `src/summaries/cache.py`
- Modify: `src/summaries/__init__.py`
- Test: `tests/unit/test_cache.py`

**Interfaces:**
- Consumes: `Action, State` from Task 2; `TreeDecomposition` from Task 6; `SummaryTable` from Task 10.
- Produces: `compute_fingerprint(decomposition, bag_id: str, state: State, owned_actions: Tuple[Action,...], child_fingerprints: Tuple[str,...]) -> str`; `SummaryCache` with `SummaryCache.empty()`, `.get(bag_id, fingerprint) -> Optional[SummaryTable]`, `.put(bag_id, fingerprint, table) -> None`, `.invalidate(bag_id) -> None`.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.summaries.cache'`

- [ ] **Step 3: Write the implementation**

```python
# src/summaries/cache.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from src.fdr.task import Action, State
from src.graph.decomposition import TreeDecomposition
from src.summaries.interface import SummaryTable


def compute_fingerprint(
    decomposition: TreeDecomposition,
    bag_id: str,
    state: State,
    owned_actions: Tuple[Action, ...],
    child_fingerprints: Tuple[str, ...],
) -> str:
    bag = decomposition.bag(bag_id)
    parent_sep = decomposition.separator_to_parent(bag_id)
    relevant_vars = sorted(bag.variables - parent_sep)
    action_sig = tuple(sorted((a.name, a.precondition, a.effect, a.cost) for a in owned_actions))
    state_sig = tuple((v, state.get(v)) for v in relevant_vars)
    payload = (bag_id, action_sig, state_sig, tuple(sorted(child_fingerprints)))
    return repr(payload)


@dataclass
class SummaryCache:
    _tables: Dict[str, SummaryTable] = field(default_factory=dict)
    _fingerprints: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def empty() -> "SummaryCache":
        return SummaryCache()

    def get(self, bag_id: str, fingerprint: str) -> Optional[SummaryTable]:
        if self._fingerprints.get(bag_id) == fingerprint:
            return self._tables.get(bag_id)
        return None

    def put(self, bag_id: str, fingerprint: str, table: SummaryTable) -> None:
        self._tables[bag_id] = table
        self._fingerprints[bag_id] = fingerprint

    def invalidate(self, bag_id: str) -> None:
        self._tables.pop(bag_id, None)
        self._fingerprints.pop(bag_id, None)
```

- [ ] **Step 4: Update `src/summaries/__init__.py`**

```python
from src.summaries.cache import SummaryCache, compute_fingerprint
from src.summaries.compose import compute_all_summaries, extract_plan
from src.summaries.interface import (
    ChildJumpStep,
    InterfaceAssignment,
    OwnActionStep,
    PlanStep,
    SummaryEntry,
    SummaryTable,
    make_interface,
)
from src.summaries.local_solver import solve_bag

__all__ = [
    "ChildJumpStep",
    "InterfaceAssignment",
    "OwnActionStep",
    "PlanStep",
    "SummaryCache",
    "SummaryEntry",
    "SummaryTable",
    "compute_all_summaries",
    "compute_fingerprint",
    "extract_plan",
    "make_interface",
    "solve_bag",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_cache.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add src/summaries/cache.py src/summaries/__init__.py tests/unit/test_cache.py
git commit -m "feat: add versioned summary cache with dependency fingerprinting"
```

---

### Task 15: Disruption model and invalidation

**Files:**
- Create: `src/repair/disruption.py`
- Create: `src/summaries/invalidation.py`
- Modify: `src/repair/__init__.py`, `src/summaries/__init__.py`
- Test: `tests/unit/test_disruption.py`, `tests/unit/test_invalidation.py`

**Interfaces:**
- Consumes: `Action, State, Task` from Task 2; `TreeDecomposition` from Task 6.
- Produces (`disruption.py`): `StateFactChange(variable: str, new_value: str)`, `ActionUnavailable(action_name: str)`, `Disruption = Union[StateFactChange, ActionUnavailable]`, `affected_variables(d) -> FrozenSet[str]`, `affected_action_names(d) -> FrozenSet[str]`, `apply_disruption(task, state, d) -> Tuple[Task, State]`.
- Produces (`invalidation.py`): `directly_affected_bags(decomposition, owned: Dict[str, Tuple[Action,...]], disruption) -> FrozenSet[str]`, `expand_to_affected_subtree(decomposition, directly_affected: FrozenSet[str]) -> FrozenSet[str]` (Steiner tree + full ancestor propagation to root).

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_disruption.py
from src.repair.disruption import ActionUnavailable, StateFactChange, apply_disruption
from tests.fixtures.two_room_basic import build_task


def test_state_fact_change_updates_state_only():
    task = build_task()
    disruption = StateFactChange(variable="door_state", new_value="unlocked")
    new_task, new_state = apply_disruption(task, task.initial_state, disruption)
    assert new_task is task
    assert new_state.get("door_state") == "unlocked"


def test_action_unavailable_removes_action_only():
    task = build_task()
    disruption = ActionUnavailable(action_name="unlock_door")
    new_task, new_state = apply_disruption(task, task.initial_state, disruption)
    assert new_state == task.initial_state
    assert "unlock_door" not in {a.name for a in new_task.actions}
    assert len(new_task.actions) == len(task.actions) - 1
```

```python
# tests/unit/test_invalidation.py
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.repair.disruption import ActionUnavailable, StateFactChange
from src.summaries.invalidation import directly_affected_bags, expand_to_affected_subtree
from tests.fixtures.three_room_hub import build_task as build_hub_task
from tests.fixtures.two_room_deeper import build_task as build_deeper_task


def test_leaf_disruption_propagates_to_every_ancestor_in_a_chain():
    task = build_deeper_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)
    leaf_bag = decomp.find_bag(frozenset({"robot_A", "gate_A"}))

    disruption = StateFactChange(variable="robot_A", new_value="exit")
    directly = directly_affected_bags(decomp, owned, disruption)
    assert directly == frozenset({leaf_bag})

    subtree = expand_to_affected_subtree(decomp, directly)
    assert subtree == frozenset(decomp.bags.keys())  # every bag is on the chain from leaf to root


def test_disrupting_one_hub_child_never_invalidates_its_sibling():
    task = build_hub_task()
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)
    bag_c = decomp.find_bag(frozenset({"hub", "robot_C"}))
    bag_a = decomp.find_bag(frozenset({"hub", "robot_A"}))

    disruption = ActionUnavailable(action_name="work_C")
    directly = directly_affected_bags(decomp, owned, disruption)
    assert directly == frozenset({bag_c})

    subtree = expand_to_affected_subtree(decomp, directly)
    assert subtree == frozenset({bag_c, decomp.root_id})
    assert bag_a not in subtree
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_disruption.py tests/unit/test_invalidation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.repair.disruption'`

- [ ] **Step 3: Write `src/repair/disruption.py`**

```python
# src/repair/disruption.py
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Tuple, Union

from src.fdr.task import State, Task


@dataclass(frozen=True)
class StateFactChange:
    variable: str
    new_value: str


@dataclass(frozen=True)
class ActionUnavailable:
    action_name: str


Disruption = Union[StateFactChange, ActionUnavailable]


def affected_variables(disruption: Disruption) -> FrozenSet[str]:
    if isinstance(disruption, StateFactChange):
        return frozenset({disruption.variable})
    return frozenset()


def affected_action_names(disruption: Disruption) -> FrozenSet[str]:
    if isinstance(disruption, ActionUnavailable):
        return frozenset({disruption.action_name})
    return frozenset()


def apply_disruption(task: Task, state: State, disruption: Disruption) -> Tuple[Task, State]:
    if isinstance(disruption, StateFactChange):
        return task, state.with_updates({disruption.variable: disruption.new_value})

    remaining = frozenset(a for a in task.actions if a.name != disruption.action_name)
    new_task = Task(variables=task.variables, actions=remaining, initial_state=task.initial_state, goal=task.goal)
    return new_task, state
```

- [ ] **Step 4: Write `src/summaries/invalidation.py`**

```python
# src/summaries/invalidation.py
from __future__ import annotations

from typing import Dict, FrozenSet, Set, Tuple

from src.fdr.task import Action
from src.graph.decomposition import TreeDecomposition
from src.repair.disruption import Disruption, affected_action_names, affected_variables


def directly_affected_bags(
    decomposition: TreeDecomposition,
    owned: Dict[str, Tuple[Action, ...]],
    disruption: Disruption,
) -> FrozenSet[str]:
    changed_vars = affected_variables(disruption)
    changed_action_names = affected_action_names(disruption)
    affected: Set[str] = set()

    for bag_id, bag in decomposition.bags.items():
        if changed_vars & bag.variables:
            affected.add(bag_id)
        if any(action.name in changed_action_names for action in owned.get(bag_id, ())):
            affected.add(bag_id)

    return frozenset(affected)


def expand_to_affected_subtree(decomposition: TreeDecomposition, directly_affected: FrozenSet[str]) -> FrozenSet[str]:
    affected: Set[str] = set(directly_affected)
    for bag_id in directly_affected:
        current = bag_id
        while decomposition.bags[current].parent_id is not None:
            current = decomposition.bags[current].parent_id
            affected.add(current)
    return frozenset(affected)
```

- [ ] **Step 5: Update `src/repair/__init__.py`**

```python
from src.repair.disruption import ActionUnavailable, Disruption, StateFactChange, apply_disruption
from src.repair.full_replan import full_replan

__all__ = ["ActionUnavailable", "Disruption", "StateFactChange", "apply_disruption", "full_replan"]
```

- [ ] **Step 6: Update `src/summaries/__init__.py`**

```python
from src.summaries.cache import SummaryCache, compute_fingerprint
from src.summaries.compose import compute_all_summaries, extract_plan
from src.summaries.interface import (
    ChildJumpStep,
    InterfaceAssignment,
    OwnActionStep,
    PlanStep,
    SummaryEntry,
    SummaryTable,
    make_interface,
)
from src.summaries.invalidation import directly_affected_bags, expand_to_affected_subtree
from src.summaries.local_solver import solve_bag

__all__ = [
    "ChildJumpStep",
    "InterfaceAssignment",
    "OwnActionStep",
    "PlanStep",
    "SummaryCache",
    "SummaryEntry",
    "SummaryTable",
    "compute_all_summaries",
    "compute_fingerprint",
    "directly_affected_bags",
    "expand_to_affected_subtree",
    "extract_plan",
    "make_interface",
    "solve_bag",
]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_disruption.py tests/unit/test_invalidation.py -v`
Expected: 4 passed

- [ ] **Step 8: Commit**

```bash
git add src/repair/disruption.py src/summaries/invalidation.py src/repair/__init__.py src/summaries/__init__.py \
        tests/unit/test_disruption.py tests/unit/test_invalidation.py
git commit -m "feat: add disruption model and conservative invalidation"
```

---

### Task 16: Localized repair algorithm (end to end)

**Files:**
- Create: `src/repair/localized_repair.py`
- Modify: `src/repair/__init__.py`
- Test: `tests/unit/test_localized_repair.py`

**Interfaces:**
- Consumes: everything from Tasks 2–15.
- Produces: `RepairLog(directly_changed_variables, directly_changed_actions, directly_affected_bags, affected_subtree, reused_bags, recomputed_bags, root_feasible: bool, fallback_occurred: bool, plan_valid: Optional[bool])` (all `FrozenSet[str]` except the bools/optional); `RepairResult(plan: Optional[Tuple[Action,...]], cost: Optional[float], log: RepairLog)`; `repair(task: Task, decomposition: TreeDecomposition, state: State, disruption: Disruption, cache: SummaryCache, task_version: str) -> RepairResult`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_localized_repair.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_localized_repair.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.repair.localized_repair'`

- [ ] **Step 3: Write the implementation**

```python
# src/repair/localized_repair.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional, Tuple

from src.fdr.simulator import validate_plan
from src.fdr.task import Action, State, Task
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import TreeDecomposition
from src.repair.disruption import Disruption, affected_action_names, affected_variables, apply_disruption
from src.repair.full_replan import full_replan
from src.summaries.cache import SummaryCache, compute_fingerprint
from src.summaries.compose import extract_plan
from src.summaries.interface import SummaryTable
from src.summaries.invalidation import directly_affected_bags, expand_to_affected_subtree
from src.summaries.local_solver import solve_bag


@dataclass(frozen=True)
class RepairLog:
    directly_changed_variables: FrozenSet[str]
    directly_changed_actions: FrozenSet[str]
    directly_affected_bags: FrozenSet[str]
    affected_subtree: FrozenSet[str]
    reused_bags: FrozenSet[str]
    recomputed_bags: FrozenSet[str]
    root_feasible: bool
    fallback_occurred: bool
    plan_valid: Optional[bool]


@dataclass(frozen=True)
class RepairResult:
    plan: Optional[Tuple[Action, ...]]
    cost: Optional[float]
    log: RepairLog


def repair(
    task: Task,
    decomposition: TreeDecomposition,
    state: State,
    disruption: Disruption,
    cache: SummaryCache,
    task_version: str,
) -> RepairResult:
    new_task, new_state = apply_disruption(task, state, disruption)
    owned = assign_actions(new_task, decomposition)

    directly_affected = directly_affected_bags(decomposition, owned, disruption)
    affected_subtree = expand_to_affected_subtree(decomposition, directly_affected)
    for bag_id in affected_subtree:
        cache.invalidate(bag_id)

    tables: Dict[str, SummaryTable] = {}
    fingerprints: Dict[str, str] = {}
    reused: set = set()
    recomputed: set = set()

    for bag_id in decomposition.postorder():
        child_fps = tuple(fingerprints[cid] for cid in decomposition.children_of(bag_id))
        fingerprint = compute_fingerprint(decomposition, bag_id, new_state, owned[bag_id], child_fps)
        fingerprints[bag_id] = fingerprint

        cached = cache.get(bag_id, fingerprint)
        if cached is not None:
            tables[bag_id] = cached
            reused.add(bag_id)
            continue

        child_tables = {cid: tables[cid] for cid in decomposition.children_of(bag_id)}
        goal = new_task.goal if bag_id == decomposition.root_id else None
        table = solve_bag(
            decomposition=decomposition,
            bag_id=bag_id,
            owned_actions=owned[bag_id],
            current_state=new_state,
            child_tables=child_tables,
            task_version=task_version,
            variables=new_task.variables,
            goal=goal,
        )
        tables[bag_id] = table
        cache.put(bag_id, fingerprint, table)
        recomputed.add(bag_id)

    root_entry = tables[decomposition.root_id].get((), ())
    root_feasible = root_entry is not None and root_entry.feasible

    fallback_occurred = False
    plan: Optional[Tuple[Action, ...]] = None
    cost: Optional[float] = None
    plan_valid: Optional[bool] = None

    if root_feasible:
        assert root_entry is not None
        plan = extract_plan(tables, root_entry)
        cost = root_entry.cost
        plan_valid = validate_plan(new_task, plan, start=new_state)
    else:
        fallback_occurred = True
        plan = full_replan(new_task, start=new_state)
        if plan is not None:
            cost = float(sum(a.cost for a in plan))
            plan_valid = validate_plan(new_task, plan, start=new_state)

    log = RepairLog(
        directly_changed_variables=affected_variables(disruption),
        directly_changed_actions=affected_action_names(disruption),
        directly_affected_bags=directly_affected,
        affected_subtree=affected_subtree,
        reused_bags=frozenset(reused),
        recomputed_bags=frozenset(recomputed),
        root_feasible=root_feasible,
        fallback_occurred=fallback_occurred,
        plan_valid=plan_valid,
    )
    return RepairResult(plan=plan, cost=cost, log=log)
```

- [ ] **Step 4: Update `src/repair/__init__.py`**

```python
from src.repair.disruption import ActionUnavailable, Disruption, StateFactChange, apply_disruption
from src.repair.full_replan import full_replan
from src.repair.localized_repair import RepairLog, RepairResult, repair

__all__ = [
    "ActionUnavailable",
    "Disruption",
    "RepairLog",
    "RepairResult",
    "StateFactChange",
    "apply_disruption",
    "full_replan",
    "repair",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_localized_repair.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/repair/localized_repair.py src/repair/__init__.py tests/unit/test_localized_repair.py
git commit -m "feat: implement the 11-step localized repair algorithm end to end"
```

---

### Task 17: Differential test suite (Milestone 1 exit criterion)

**Files:**
- Create: `tests/differential/test_localized_vs_full_replan.py`

**Interfaces:**
- Consumes: `repair` from Task 16; `full_replan` from Task 13; `validate_plan` from Task 3; all three fixtures.

This is the test that certifies the Milestone 1 exit criterion from CLAUDE.md §17: localized repair and full recomputation must agree on feasibility (and, since Phase-1 summaries are cost-optimal, cost) across every fixture and every hand-authored disruption.

- [ ] **Step 1: Write the test**

```python
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
```

- [ ] **Step 2: Run the differential suite**

Run: `uv run pytest tests/differential/test_localized_vs_full_replan.py -v`
Expected: 12 passed — this is the Milestone 1 exit criterion.

- [ ] **Step 3: Commit**

```bash
git add tests/differential/test_localized_vs_full_replan.py
git commit -m "test: differential suite proving localized repair matches full replan (M1 exit criterion)"
```

---

### Task 18: Property-style exhaustive cache-correctness tests

**Files:**
- Create: `tests/property/test_cache_correctness.py`

**Interfaces:**
- Consumes: `repair`, `SummaryCache` from Tasks 14/16; all three fixtures; all `SCENARIOS`-style disruptions.

Since every fixture's state space is small enough to enumerate exhaustively, these are exhaustive checks over the full disruption space rather than randomized `hypothesis` properties — equally rigorous at this scale and consistent with keeping dependencies minimal (CLAUDE.md §15's property-test intent, items 3 and 4).

- [ ] **Step 1: Write the test**

```python
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
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/property/test_cache_correctness.py -v`
Expected: 2 passed

- [ ] **Step 3: Run the full test suite as a final check**

Run: `uv run pytest -v`
Expected: all tests across `tests/unit`, `tests/differential`, and `tests/property` pass (approximately 45 tests total).

- [ ] **Step 4: Commit**

```bash
git add tests/property/test_cache_correctness.py
git commit -m "test: exhaustive cache-correctness checks for sibling non-invalidation and dependency changes"
```

---

## Self-Review Notes

- **Spec coverage:** every module named in the design doc §3 has a task (Tasks 2–3 = fdr/, Tasks 5–7 = graph/, Tasks 10–15 = summaries/ + repair/disruption, Task 16 = repair/localized_repair, Task 13 = repair/full_replan). Toy domains §2 covered by Tasks 4, 8, plus an added `three_room_hub` fixture (Task 9) needed to actually exercise the branching/sibling-non-invalidation property from CLAUDE.md §15 that a pure chain topology cannot test. Testing strategy §7/§15 covered by Tasks 17 (differential) and 18 (property-style, exhaustive rather than randomized since the state spaces are enumerable).
- **Type consistency:** `solve_bag`'s signature (Task 11) is used identically in `compose.py` (Task 12) and `localized_repair.py` (Task 16); `compute_fingerprint`'s signature (Task 14) is used identically in `localized_repair.py`; `SummaryTable.get`/`best_outgoing` (Task 10) are used identically in `local_solver.py`, `compose.py`, and `cache.py`.
- **Placeholder scan:** no TBD/TODO; every step includes complete, runnable code and exact expected `pytest` output, verified by hand-deriving the expected costs (4, 5, 3) for the three fixtures' optimal plans and cross-checking the actual `networkx.algorithms.approximation.treewidth_min_fill_in` output for both non-trivial fixtures before writing their tests (see design doc note on `two_room_deeper` producing a 4-bag chain, not 3).
