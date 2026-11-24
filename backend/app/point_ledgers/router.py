from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.point_ledgers.schemas import PointsBalanceResponse, PointLedgerResponse
from app.errors.exception import PermissionDeniedError
from app.point_ledgers.schemas import PointsReconciliationResponse

from app.point_ledgers.interfaces import PointLedgerServiceInterface
from app.point_ledgers.dependencies import get_point_ledger_service

router = APIRouter(prefix="/point_ledgers", tags=["point_ledgers"])

@router.post('', status_code=status.HTTP_403_FORBIDDEN)
def create_point_ledger(current_user=Depends(get_current_user)):
  raise PermissionDeniedError("Point entries can only be posted by internal workflows")

@router.get('',response_model=list[PointLedgerResponse], status_code=status.HTTP_200_OK)
def list_point_ledgers_by_user_id(current_user = Depends(get_current_user), point_ledger_service: PointLedgerServiceInterface = Depends(get_point_ledger_service)):
  return point_ledger_service.list_point_ledgers_by_user_id(user_id=current_user.id)

@router.get('/balance', response_model=PointsBalanceResponse, status_code=status.HTTP_200_OK)
def get_points_balance(current_user = Depends(get_current_user), point_ledger_service: PointLedgerServiceInterface = Depends(get_point_ledger_service)):
  balance = point_ledger_service.get_user_balance(user_id=current_user.id)
  return PointsBalanceResponse(balance=balance)


@router.get('/reconciliation', response_model=PointsReconciliationResponse)
def get_points_reconciliation(
  current_user=Depends(get_current_user),
  point_ledger_service: PointLedgerServiceInterface = Depends(get_point_ledger_service),
):
  return point_ledger_service.get_balance_reconciliation(user_id=current_user.id)
