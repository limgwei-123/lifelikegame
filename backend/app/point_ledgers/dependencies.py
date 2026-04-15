from app.db import get_db
from fastapi import Depends
from sqlalchemy.orm import Session

from app.point_ledgers.interfaces import PointLedgerServiceInterface
from app.point_ledgers.repository import PointLedgerRepository
from app.point_ledgers.service import PointLedgerService

def build_point_ledger_service(db: Session) -> PointLedgerServiceInterface:
    return PointLedgerService(
        point_ledger_repo=PointLedgerRepository(db),
    )

def get_point_ledger_service(db: Session = Depends(get_db))->PointLedgerServiceInterface:
  return build_point_ledger_service(db)