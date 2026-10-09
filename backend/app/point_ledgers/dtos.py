from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PointsReconciliationDTO:
    cached_balance: int | None
    ledger_balance: int

    @property
    def difference(self) -> int | None:
        if self.cached_balance is None:
            return None
        return self.cached_balance - self.ledger_balance

    @property
    def is_consistent(self) -> bool:
        return self.difference == 0
