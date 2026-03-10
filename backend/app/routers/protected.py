from fastapi  import APIRouter, Depends

from app.auth.deps import get_current_user

router = APIRouter(
  dependencies=[Depends(get_current_user)]
)