"""Synthetic hub-and-spoke tasks for cache-reuse / amortization studies.

Topology: k independent worker regions coordinate through one shared hub
separator. Disrupting one leaf invalidates only that leaf and the root bag,
leaving sibling subtrees reusable from cache.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.fdr.task import Action, Task, Variable


@dataclass(frozen=True)
class HubRegionConfig:
    num_workers: int = 4
    local_domain_size: int = 3
    separator_domain_size: int = 2
    instance_id: str = "hub_default"

    def __post_init__(self) -> None:
        if self.num_workers < 2:
            raise ValueError("num_workers must be at least 2")
        if self.local_domain_size < 2:
            raise ValueError("local_domain_size must be at least 2")
        if self.separator_domain_size < 2:
            raise ValueError("separator_domain_size must be at least 2")


def _local_values(size: int) -> tuple[str, ...]:
    return tuple(f"w{i}" for i in range(size))


def _separator_values(size: int) -> tuple[str, ...]:
    return tuple(f"h{i}" for i in range(size))


def build_hub_task(config: HubRegionConfig) -> Task:
    local_vals = _local_values(config.local_domain_size)
    sep_vals = _separator_values(config.separator_domain_size)
    idle, ready = sep_vals[0], sep_vals[-1]

    variables = [
        Variable(name="hub", domain=frozenset(sep_vals)),
        Variable(name="goal_robot", domain=frozenset({"start", "done"})),
    ]
    for i in range(config.num_workers):
        variables.append(Variable(name=f"worker_{i}", domain=frozenset(local_vals)))

    actions: list[Action] = []
    for i in range(config.num_workers):
        for j in range(len(local_vals) - 1):
            actions.append(
                Action.create(
                    f"advance_w{i}_from_{local_vals[j]}_to_{local_vals[j + 1]}",
                    {f"worker_{i}": local_vals[j], "hub": idle},
                    {f"worker_{i}": local_vals[j + 1]},
                )
            )
        actions.append(
            Action.create(
                f"mark_ready_w{i}",
                {f"worker_{i}": local_vals[-1], "hub": idle},
                {"hub": ready},
            )
        )

    actions.append(
        Action.create(
            "finish_goal",
            {"hub": ready, "goal_robot": "start"},
            {"goal_robot": "done"},
        )
    )

    initial = {"hub": idle, "goal_robot": "start"}
    for i in range(config.num_workers):
        initial[f"worker_{i}"] = local_vals[0]

    return Task.create(
        variables=variables,
        actions=actions,
        initial_state=initial,
        goal={"goal_robot": "done"},
    )


def worker_name(worker_index: int) -> str:
    return f"worker_{worker_index}"


def worker_disruption_state_fact(worker_index: int, config: HubRegionConfig) -> tuple[str, str]:
    local_vals = _local_values(config.local_domain_size)
    mid = local_vals[len(local_vals) // 2]
    return worker_name(worker_index), mid
