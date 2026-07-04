from __future__ import annotations

from pathlib import Path

from src.experiments.metrics import RunRecord


def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            "matplotlib is required for plotting; install with: uv sync --group dev"
        ) from exc
    return plt


def plot_repair_time_vs_affected_bags(records: list[RunRecord], out_path: Path) -> Path:
    """Plot 1 from CLAUDE.md §13: repair time vs affected subtree size."""
    plt = _require_matplotlib()

    localized = [r for r in records if r.method == "localized" and r.domain == "synthetic_chain"]
    full = [r for r in records if r.method == "full_replan" and r.domain == "synthetic_chain"]

    fig, ax = plt.subplots(figsize=(8, 5))
    if localized:
        ax.scatter(
            [r.affected_bag_count for r in localized],
            [r.repair_seconds for r in localized],
            label="localized",
            alpha=0.8,
        )
    if full:
        ax.scatter(
            [r.affected_bag_count for r in full],
            [r.repair_seconds for r in full],
            label="full_replan",
            alpha=0.8,
            marker="x",
        )
    ax.set_xlabel("Affected bag count")
    ax.set_ylabel("Repair time (seconds)")
    ax.set_title("Repair time vs affected subtree size")
    ax.legend()
    ax.grid(True, alpha=0.3)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_cumulative_amortization(summary, out_path: Path) -> Path:
    """Plot 3 from CLAUDE.md §13: cumulative time vs number of disruptions."""
    plt = _require_matplotlib()

    localized_records = [r for r in summary.records if r.method == "localized"]
    full_records = [r for r in summary.records if r.method == "full_replan"]

    def cumulative(records: list[RunRecord]) -> tuple[list[int], list[float]]:
        xs: list[int] = []
        ys: list[float] = []
        total = records[0].preprocess_seconds if records else 0.0
        for idx, record in enumerate(records, start=1):
            total += record.repair_seconds
            xs.append(idx)
            ys.append(total)
        return xs, ys

    loc_x, loc_y = cumulative(localized_records)
    full_x, full_y = cumulative(full_records)

    fig, ax = plt.subplots(figsize=(8, 5))
    if loc_x:
        ax.plot(loc_x, loc_y, marker="o", label="localized (incl. preprocess)")
    if full_x:
        ax.plot(full_x, full_y, marker="x", label="full_replan")
    ax.set_xlabel("Number of disruptions")
    ax.set_ylabel("Cumulative time (seconds)")
    ax.set_title("Amortization: localized repair vs full replanning")
    ax.legend()
    ax.grid(True, alpha=0.3)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
