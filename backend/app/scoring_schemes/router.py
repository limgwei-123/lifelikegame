from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.scoring_schemes.schemas import (
  CreateScoringSchemeRequest,
  UpdateScoringSchemeRequest,
  ScoringSchemeResponse
)

from app.scoring_schemes.interfaces import ScoringSchemeServiceInterface
from app.scoring_schemes.dependencies import get_scoring_scheme_service

router = APIRouter(prefix="/scoring_schemes",tags=["scoring_schemes"])

@router.post('', response_model=ScoringSchemeResponse, status_code=status.HTTP_201_CREATED)
def create_scoring_scheme(payload: CreateScoringSchemeRequest, current_user = Depends(get_current_user), scoring_scheme_service: ScoringSchemeServiceInterface = Depends(get_scoring_scheme_service)):
  return scoring_scheme_service.create_scoring_scheme(
    user_id=current_user.id, payload=payload
  )

@router.get('/{scoring_scheme_id}')
def get_scoring_scheme_by_id(scoring_scheme_id, current_user = Depends(get_current_user), scoring_scheme_service: ScoringSchemeServiceInterface = Depends(get_scoring_scheme_service)):
  return scoring_scheme_service.get_scoring_scheme_by_id(scoring_scheme_id=scoring_scheme_id, user_id= current_user.id)

@router.get('')
def list_scoring_schemes_by_user_id(current_user = Depends(get_current_user), scoring_scheme_service: ScoringSchemeServiceInterface = Depends(get_scoring_scheme_service)):
  return scoring_scheme_service.list_scoring_schemes_by_user_id(user_id=current_user.id)

@router.post('/{scoring_scheme_id}', response_model=ScoringSchemeResponse, status_code=status.HTTP_200_OK)
def update_scoring_scheme(scoring_scheme_id, paylod: UpdateScoringSchemeRequest, current_user = Depends(get_current_user), scoring_scheme_service: ScoringSchemeServiceInterface = Depends(get_scoring_scheme_service)):
  return scoring_scheme_service.update_scoring_scheme(
    scoring_scheme_id=scoring_scheme_id,
    user_id=current_user.id,
    data=paylod
  )

@router.post("/{scoring_scheme_id}/delete", status_code = status.HTTP_204_NO_CONTENT)
def delete_scoring_scheme(
  scoring_scheme_id,
  current_user = Depends(get_current_user), scoring_scheme_service: ScoringSchemeServiceInterface = Depends(get_scoring_scheme_service)
):
  scoring_scheme_service.delete_scoring_scheme(scoring_scheme_id=scoring_scheme_id, user_id=current_user.id)