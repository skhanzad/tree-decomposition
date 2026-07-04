from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from src.fdr.task import Task
from src.graph.decomposition import TreeDecomposition
from src.repair.disruption import Disruption
from src.repair.localized_repair import RepairResult
from src.summaries.cache import SummaryCache


@dataclass(frozen=True)
class RunRecord:
    git_commit: str
    instance_id: str
    domain: str
    seed: int
    disruption_id: str
    disruption_type: str
    decomposition_method: str
    global_treewidth_estimate: int
    affected_bag_count: int
    affected_separator_max: int
    method: str
    timeout_seconds: float
    success: bool
    plan_valid: bool
    preprocess_seconds: float
    repair_seconds: float
    total_seconds: float
    cache_hits: int
    cache_misses: int
    peak_memory_mb: float = 0.0
    recomputed_bags: int = 0
    reused_bags: int = 0
    plan_cost: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def git_commit_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"


def disruption_type_name(disruption: Disruption) -> str:
    return type(disruption).__name__


def disruption_id(disruption: Disruption) -> str:
    if hasattr(disruption, "variable"):
        return f"{disruption.variable}:={disruption.new_value}"  # type: ignore[attr-defined]
    if hasattr(disruption, "action_name"):
        return f"unavailable:{disruption.action_name}"  # type: ignore[attr-defined]
    return repr(disruption)


def estimate_global_treewidth(decomposition: TreeDecomposition) -> int:
    if not decomposition.bags:
        return 0
    return max(len(bag.variables) - 1 for bag in decomposition.bags.values())


def max_affected_separator_size(decomposition: TreeDecomposition, affected_subtree: frozenset[str]) -> int:
    sizes = [len(decomposition.separator_to_parent(bag_id)) for bag_id in affected_subtree]
    return max(sizes) if sizes else 0


class TimedCache(SummaryCache):
    """SummaryCache wrapper that counts hits and misses."""

    def __init__(self) -> None:
        super().__init__()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def empty() -> "TimedCache":
        return TimedCache()

    def get(self, bag_id: str, fingerprint: str):
        result = super().get(bag_id, fingerprint)
        if result is not None:
            self.hits += 1
        else:
            self.misses += 1
        return result


def time_call(fn, *args, **kwargs) -> tuple[float, Any]:
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return time.perf_counter() - start, result


def make_run_record(
    *,
    instance_id: str,
    domain: str,
    seed: int,
    disruption: Disruption,
    decomposition: TreeDecomposition,
    method: str,
    preprocess_seconds: float,
    repair_seconds: float,
    cache: TimedCache,
    repair_result: RepairResult,
    timeout_seconds: float = 300.0,
) -> RunRecord:
    log = repair_result.log
    plan_valid = repair_result.log.plan_valid is True
    success = repair_result.plan is not None and plan_valid

    return RunRecord(
        git_commit=git_commit_hash(),
        instance_id=instance_id,
        domain=domain,
        seed=seed,
        disruption_id=disruption_id(disruption),
        disruption_type=disruption_type_name(disruption),
        decomposition_method="min_fill",
        global_treewidth_estimate=estimate_global_treewidth(decomposition),
        affected_bag_count=len(log.affected_subtree),
        affected_separator_max=max_affected_separator_size(decomposition, log.affected_subtree),
        method=method,
        timeout_seconds=timeout_seconds,
        success=success,
        plan_valid=plan_valid,
        preprocess_seconds=preprocess_seconds,
        repair_seconds=repair_seconds,
        total_seconds=preprocess_seconds + repair_seconds,
        cache_hits=cache.hits,
        cache_misses=cache.misses,
        recomputed_bags=len(log.recomputed_bags),
        reused_bags=len(log.reused_bags),
        plan_cost=repair_result.cost,
    )


def write_jsonl(records: list[RunRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict()) + "\n")
