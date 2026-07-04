"""Synthetic chain-of-regions tasks for locality sweeps.

Topology: robot_0 - gate_0 - robot_1 - ... - robot_{k-1}
Each region has a local progress variable; gates are shared separators.
Disrupting a region near the goal affects a small subtree; disrupting an
early region propagates invalidation toward the root.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.fdr.task import Action, Task, Variable


@dataclass(frozen=True)
class ChainRegionConfig:
    num_regions: int = 4
    local_domain_size: int = 3
    separator_domain_size: int = 2
    instance_id: str = "chain_default"

    def __post_init__(self) -> None:
        if self.num_regions < 2:
            raise ValueError("num_regions must be at least 2")
        if self.local_domain_size < 2:
            raise ValueError("local_domain_size must be at least 2")
        if self.separator_domain_size < 2:
            raise ValueError("separator_domain_size must be at least 2")


def _local_values(size: int) -> tuple[str, ...]:
    return tuple(f"p{i}" for i in range(size))


def _separator_values(size: int) -> tuple[str, ...]:
    return tuple(f"s{i}" for i in range(size))


def build_chain_task(config: ChainRegionConfig) -> Task:
    local_vals = _local_values(config.local_domain_size)
    sep_vals = _separator_values(config.separator_domain_size)
    closed, open_ = sep_vals[0], sep_vals[-1]

    variables: list[Variable] = []
    actions: list[Action] = []

    for i in range(config.num_regions):
        variables.append(Variable(name=f"robot_{i}", domain=frozenset(local_vals)))
        if i < config.num_regions - 1:
            variables.append(Variable(name=f"gate_{i}", domain=frozenset(sep_vals)))

    for i in range(config.num_regions):
        for j in range(len(local_vals) - 1):
            pre: dict[str, str] = {f"robot_{i}": local_vals[j]}
            if i > 0:
                pre[f"gate_{i - 1}"] = open_
            elif i < config.num_regions - 1:
                pre[f"gate_{i}"] = closed
            actions.append(
                Action.create(
                    f"move_r{i}_from_{local_vals[j]}_to_{local_vals[j + 1]}",
                    pre,
                    {f"robot_{i}": local_vals[j + 1]},
                )
            )
        if i < config.num_regions - 1:
            actions.append(
                Action.create(
                    f"open_gate_{i}",
                    {f"robot_{i}": local_vals[-1], f"gate_{i}": closed},
                    {f"gate_{i}": open_},
                )
            )

    initial = {f"robot_{i}": local_vals[0] for i in range(config.num_regions)}
    for i in range(config.num_regions - 1):
        initial[f"gate_{i}"] = closed

    goal = {f"robot_{config.num_regions - 1}": local_vals[-1]}

    return Task.create(
        variables=variables,
        actions=actions,
        initial_state=initial,
        goal=goal,
    )


def region_robot_name(region_index: int) -> str:
    return f"robot_{region_index}"


def region_disruption_state_fact(region_index: int, config: ChainRegionConfig) -> tuple[str, str]:
    """Return a state-fact change on a region-local variable (mid progress)."""
    local_vals = _local_values(config.local_domain_size)
    mid = local_vals[len(local_vals) // 2]
    return region_robot_name(region_index), mid
