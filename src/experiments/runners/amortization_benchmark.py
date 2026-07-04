from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.experiments.generators.hub_regions import (
    HubRegionConfig,
    build_hub_task,
    worker_disruption_state_fact,
)
from src.experiments.metrics import RunRecord, TimedCache, make_run_record, time_call
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.repair.baselines import repair_full_replan
from src.repair.disruption import StateFactChange
from src.repair.localized_repair import repair
from src.summaries.preprocess import build_initial_cache


@dataclass(frozen=True)
class AmortizationConfig:
    num_workers: int = 6
    local_domain_size: int = 4
    separator_domain_size: int = 2
    num_disruptions: int = 5
    seed: int = 0


@dataclass(frozen=True)
class AmortizationSummary:
    preprocess_seconds: float
    localized_total_repair_seconds: float
    full_replan_total_repair_seconds: float
    localized_cumulative_seconds: float
    full_replan_cumulative_seconds: float
    break_even_disruption_index: int | None
    records: tuple[RunRecord, ...]


def run_amortization_study(config: AmortizationConfig | None = None) -> AmortizationSummary:
    """Experiment B: repeated local disruptions on a hub task with warm cache."""
    cfg = config or AmortizationConfig()
    hub_cfg = HubRegionConfig(
        num_workers=cfg.num_workers,
        local_domain_size=cfg.local_domain_size,
        separator_domain_size=cfg.separator_domain_size,
        instance_id=f"hub_w{cfg.num_workers}",
    )
    task = build_hub_task(hub_cfg)
    decomp = build_decomposition(task, build_interaction_graph(task))

    cache = TimedCache.empty()
    preprocess_seconds, _ = time_call(
        build_initial_cache, task, decomp, cache, "v1", task.initial_state
    )

    records: list[RunRecord] = []
    localized_repair_total = 0.0
    full_replan_total = 0.0
    break_even: int | None = None

    worker_indices = list(range(min(cfg.num_disruptions, cfg.num_workers)))

    for step, worker_index in enumerate(worker_indices):
        var, val = worker_disruption_state_fact(worker_index, hub_cfg)
        disruption = StateFactChange(variable=var, new_value=val)
        instance_id = f"{hub_cfg.instance_id}_step{step}"

        repair_seconds, localized_result = time_call(
            repair, task, decomp, task.initial_state, disruption, cache, "v1"
        )
        localized_repair_total += repair_seconds
        records.append(
            make_run_record(
                instance_id=instance_id,
                domain="synthetic_hub",
                seed=cfg.seed,
                disruption=disruption,
                decomposition=decomp,
                method="localized",
                preprocess_seconds=preprocess_seconds if step == 0 else 0.0,
                repair_seconds=repair_seconds,
                cache=cache,
                repair_result=localized_result,
            )
        )

        full_seconds, full_result = time_call(
            repair_full_replan, task, task.initial_state, disruption
        )
        full_replan_total += full_seconds
        records.append(
            make_run_record(
                instance_id=instance_id,
                domain="synthetic_hub",
                seed=cfg.seed,
                disruption=disruption,
                decomposition=decomp,
                method="full_replan",
                preprocess_seconds=0.0,
                repair_seconds=full_seconds,
                cache=TimedCache.empty(),
                repair_result=full_result,
            )
        )

        localized_cumulative = preprocess_seconds + localized_repair_total
        full_cumulative = full_replan_total
        if break_even is None and localized_cumulative < full_cumulative:
            break_even = step + 1

    return AmortizationSummary(
        preprocess_seconds=preprocess_seconds,
        localized_total_repair_seconds=localized_repair_total,
        full_replan_total_repair_seconds=full_replan_total,
        localized_cumulative_seconds=preprocess_seconds + localized_repair_total,
        full_replan_cumulative_seconds=full_replan_total,
        break_even_disruption_index=break_even,
        records=tuple(records),
    )
