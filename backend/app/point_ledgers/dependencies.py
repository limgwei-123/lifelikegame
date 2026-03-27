from app.db import get_db
from fastapi import Depends
from sqlalchemy.orm import Session

from app.point_ledgers.interfaces import PointLedgerServiceInterface
from app.point_ledgers.repository import PointLedgerRepository
from app.point_ledgers.service import PointLedgerService

def get_point_ledger_repository(db: Session = Depends(get_db))->PointLedgerRepository:
  return PointLedgerRepository(db)

def get_point_ledger_service(point_ledger_repo: PointLedgerRepository = Depends(get_point_ledger_repository))->PointLedgerServiceInterface:
  return PointLedgerService(point_ledger_repo= point_ledger_repo)