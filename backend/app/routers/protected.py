from fastapi  import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.goals.router import router as goal_router
from app.users.router import router as user_router
from app.tasks.router import router as task_router

router = APIRouter(
  dependencies=[Depends(get_current_user)]
)
router.include_router(goal_router)
router.include_router(user_router)
router.include_router(task_router)