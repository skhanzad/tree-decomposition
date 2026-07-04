from src.repair.disruption import ActionUnavailable, Disruption, StateFactChange, apply_disruption
from src.repair.full_replan import full_replan

def __getattr__(name: str):
    if name == "RepairLog":
        from src.repair.localized_repair import RepairLog
        return RepairLog
    elif name == "RepairResult":
        from src.repair.localized_repair import RepairResult
        return RepairResult
    elif name == "repair":
        from src.repair.localized_repair import repair
        return repair
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
