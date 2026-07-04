from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from src.experiments.generators.chain_regions import (
    ChainRegionConfig,
    build_chain_task,
    region_disruption_state_fact,
)
from src.experiments.generators.hub_regions import HubRegionConfig
from src.experiments.metrics import RunRecord, TimedCache, make_run_record, time_call
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.repair.baselines import repair_full_replan, repair_no_cache
from src.repair.disruption import StateFactChange
from src.repair.localized_repair import repair
from src.summaries.preprocess import build_initial_cache


@dataclass(frozen=True)
class LocalitySweepConfig:
    num_regions: Sequence[int] = (3, 4, 5, 6)
    local_domain_size: int = 3
    separator_domain_size: int = 2
    seed: int = 0


def run_locality_sweep(config: LocalitySweepConfig | None = None) -> list[RunRecord]:
    """Experiment A: sweep disruption location on chain tasks (affected subtree size)."""
    cfg = config or LocalitySweepConfig()
    records: list[RunRecord] = []

    for num_regions in cfg.num_regions:
        chain_cfg = ChainRegionConfig(
            num_regions=num_regions,
            local_domain_size=cfg.local_domain_size,
            separator_domain_size=cfg.separator_domain_size,
            instance_id=f"chain_k{num_regions}",
        )
        task = build_chain_task(chain_cfg)
        decomp = build_decomposition(task, build_interaction_graph(task))

        for region_index in range(num_regions):
            var, val = region_disruption_state_fact(region_index, chain_cfg)
            disruption = StateFactChange(variable=var, new_value=val)
            instance_id = f"{chain_cfg.instance_id}_r{region_index}"

            for method, runner in (
                ("localized", _run_localized),
                ("full_replan", _run_full_replan),
                ("no_cache", _run_no_cache),
            ):
                records.append(
                    runner(
                        task=task,
                        decomp=decomp,
                        disruption=disruption,
                        instance_id=instance_id,
                        domain="synthetic_chain",
                        seed=cfg.seed,
                        method=method,
                    )
                )

    return records


def _run_localized(**kwargs) -> RunRecord:
    task = kwargs["task"]
    decomp = kwargs["decomp"]
    disruption = kwargs["disruption"]
    cache = TimedCache.empty()
    preprocess_seconds, _ = time_call(
        build_initial_cache, task, decomp, cache, "v1", task.initial_state
    )
    repair_seconds, result = time_call(
        repair, task, decomp, task.initial_state, disruption, cache, "v1"
    )
    return make_run_record(
        instance_id=kwargs["instance_id"],
        domain=kwargs["domain"],
        seed=kwargs["seed"],
        disruption=disruption,
        decomposition=decomp,
        method=kwargs["method"],
        preprocess_seconds=preprocess_seconds,
        repair_seconds=repair_seconds,
        cache=cache,
        repair_result=result,
    )


def _run_no_cache(**kwargs) -> RunRecord:
    task = kwargs["task"]
    decomp = kwargs["decomp"]
    disruption = kwargs["disruption"]
    cache = TimedCache.empty()
    preprocess_seconds, _ = time_call(
        build_initial_cache, task, decomp, cache, "v1", task.initial_state
    )
    repair_seconds, result = time_call(
        repair_no_cache, task, decomp, task.initial_state, disruption, cache, "v1"
    )
    return make_run_record(
        instance_id=kwargs["instance_id"],
        domain=kwargs["domain"],
        seed=kwargs["seed"],
        disruption=disruption,
        decomposition=decomp,
        method=kwargs["method"],
        preprocess_seconds=preprocess_seconds,
        repair_seconds=repair_seconds,
        cache=cache,
        repair_result=result,
    )


def _run_full_replan(**kwargs) -> RunRecord:
    task = kwargs["task"]
    decomp = kwargs["decomp"]
    disruption = kwargs["disruption"]
    repair_seconds, result = time_call(repair_full_replan, task, task.initial_state, disruption)
    return make_run_record(
        instance_id=kwargs["instance_id"],
        domain=kwargs["domain"],
        seed=kwargs["seed"],
        disruption=disruption,
        decomposition=decomp,
        method=kwargs["method"],
        preprocess_seconds=0.0,
        repair_seconds=repair_seconds,
        cache=TimedCache.empty(),
        repair_result=result,
    )
