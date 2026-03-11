from fastapi  import APIRouter, Depends

from app.auth.deps import get_current_user
from app.goals.router import router as goal_router

router = APIRouter(
  dependencies=[Depends(get_current_user)]
)
router.include_router(goal_router)