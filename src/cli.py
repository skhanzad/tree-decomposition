from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.experiments.metrics import write_jsonl
from src.experiments.plotting import plot_cumulative_amortization, plot_repair_time_vs_affected_bags
from src.experiments.runners.amortization_benchmark import AmortizationConfig, run_amortization_study
from src.experiments.runners.locality_benchmark import LocalitySweepConfig, run_locality_sweep


def cmd_benchmark(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    locality_cfg = LocalitySweepConfig(
        num_regions=tuple(int(x) for x in args.regions.split(",")),
        local_domain_size=args.local_domain_size,
        separator_domain_size=args.separator_domain_size,
        seed=args.seed,
    )
    locality_records = run_locality_sweep(locality_cfg)
    write_jsonl(locality_records, out_dir / "locality_sweep.jsonl")

    amort_cfg = AmortizationConfig(
        num_workers=args.num_workers,
        local_domain_size=args.local_domain_size,
        separator_domain_size=args.separator_domain_size,
        num_disruptions=args.num_disruptions,
        seed=args.seed,
    )
    amort_summary = run_amortization_study(amort_cfg)
    write_jsonl(list(amort_summary.records), out_dir / "amortization.jsonl")

    summary_path = out_dir / "amortization_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "preprocess_seconds": amort_summary.preprocess_seconds,
                "localized_total_repair_seconds": amort_summary.localized_total_repair_seconds,
                "full_replan_total_repair_seconds": amort_summary.full_replan_total_repair_seconds,
                "localized_cumulative_seconds": amort_summary.localized_cumulative_seconds,
                "full_replan_cumulative_seconds": amort_summary.full_replan_cumulative_seconds,
                "break_even_disruption_index": amort_summary.break_even_disruption_index,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if args.plot:
        figures_dir = out_dir / "figures"
        plot_repair_time_vs_affected_bags(locality_records, figures_dir / "repair_time_vs_affected_bags.png")
        plot_cumulative_amortization(amort_summary, figures_dir / "cumulative_amortization.png")

    print(f"Wrote {len(locality_records)} locality records to {out_dir / 'locality_sweep.jsonl'}")
    print(f"Wrote amortization summary to {summary_path}")
    if amort_summary.break_even_disruption_index is not None:
        print(
            "Break-even after disruption "
            f"{amort_summary.break_even_disruption_index}: "
            f"localized cumulative {amort_summary.localized_cumulative_seconds:.4f}s "
            f"< full replan {amort_summary.full_replan_cumulative_seconds:.4f}s"
        )
    else:
        print("Warning: localized repair did not beat full replan within the sweep.")
    return 0


def cmd_plot(args: argparse.Namespace) -> int:
    import json as json_mod

    results_dir = Path(args.results)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    locality_path = results_dir / "locality_sweep.jsonl"
    amort_path = results_dir / "amortization.jsonl"
    summary_path = results_dir / "amortization_summary.json"

    if not locality_path.exists():
        print(f"Missing {locality_path}", file=sys.stderr)
        return 1

    from src.experiments.metrics import RunRecord

    locality_records = [RunRecord(**json_mod.loads(line)) for line in locality_path.read_text().splitlines() if line.strip()]
    plot_repair_time_vs_affected_bags(locality_records, out_dir / "repair_time_vs_affected_bags.png")

    if amort_path.exists() and summary_path.exists():
        from src.experiments.runners.amortization_benchmark import AmortizationSummary

        amort_records = [RunRecord(**json_mod.loads(line)) for line in amort_path.read_text().splitlines() if line.strip()]
        summary_data = json_mod.loads(summary_path.read_text())
        summary = AmortizationSummary(records=tuple(amort_records), **summary_data)
        plot_cumulative_amortization(summary, out_dir / "cumulative_amortization.png")

    print(f"Figures written to {out_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    benchmark = sub.add_parser("benchmark", help="Run Milestone 2 synthetic locality benchmarks")
    benchmark.add_argument("--out", default="results/milestone2", help="Output directory for JSONL logs")
    benchmark.add_argument("--regions", default="3,4,5,6", help="Comma-separated chain region counts")
    benchmark.add_argument("--num-workers", type=int, default=6, help="Hub worker count for amortization")
    benchmark.add_argument("--num-disruptions", type=int, default=5, help="Repeated disruptions per hub instance")
    benchmark.add_argument("--local-domain-size", type=int, default=4)
    benchmark.add_argument("--separator-domain-size", type=int, default=2)
    benchmark.add_argument("--seed", type=int, default=0)
    benchmark.add_argument("--plot", action="store_true", help="Also write figures under out/figures/")
    benchmark.set_defaults(func=cmd_benchmark)

    plot = sub.add_parser("plot", help="Regenerate figures from benchmark JSONL logs")
    plot.add_argument("--results", default="results/milestone2", help="Directory with benchmark JSONL logs")
    plot.add_argument("--out", default="figures/milestone2", help="Directory for PNG figures")
    plot.set_defaults(func=cmd_plot)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
