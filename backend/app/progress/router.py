from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.progress.dependencies import get_progress_service
from app.progress.schemas import ProgressResponse
from app.progress.service import ProgressService


router = APIRouter(prefix='/progress', tags=['progress'])


@router.get('', response_model=ProgressResponse)
def get_player_progress(
    current_user=Depends(get_current_user),
    progress_service: ProgressService = Depends(get_progress_service),
):
    return progress_service.get_progress(current_user.id)
