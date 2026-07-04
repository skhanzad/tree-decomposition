"""Milestone 2 exit criterion: localized repair beats full replan after amortization."""
from src.experiments.runners.amortization_benchmark import AmortizationConfig, run_amortization_study
from src.experiments.runners.locality_benchmark import LocalitySweepConfig, run_locality_sweep


def test_locality_sweep_produces_records_for_all_methods():
    records = run_locality_sweep(LocalitySweepConfig(num_regions=(3, 4), local_domain_size=3))
    methods = {r.method for r in records}
    assert methods == {"localized", "full_replan", "no_cache"}
    assert all(r.affected_bag_count >= 1 for r in records if r.method == "localized")


def test_amortized_localized_repair_beats_repeated_full_replan():
    summary = run_amortization_study(
        AmortizationConfig(
            num_workers=6,
            local_domain_size=4,
            separator_domain_size=2,
            num_disruptions=5,
        )
    )
    assert summary.break_even_disruption_index is not None
    assert summary.localized_cumulative_seconds < summary.full_replan_cumulative_seconds
