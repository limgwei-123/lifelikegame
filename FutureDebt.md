- repo的naming要改的简洁一点
- 未来要开dto
- item pass进去repo最好是这样
✅ Router：用 schema 做 validation → 转成 DTO → 传给 service

@router.post('/goals/{goal_id}/tasks')
def create_task(
    goal_id: int,
    payload: CreateTaskRequest,
    current_user=Depends(get_current_user),
    task_workflow_service: TaskWorkflowServiceInterface = Depends(get_task_workflow_service),
):
    dto = CreateTaskDTO(
        goal_id=goal_id,
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        is_active=payload.is_active,
        scoring_scheme_id=payload.scoring_scheme_id,
        scoring_scheme_json=payload.scoring_scheme_json,
        is_scoring_scheme_locked=payload.is_scoring_scheme_locked,
        schedule=payload.schedule,  # 可以先保留 schema（过渡OK）
    )

    return task_workflow_service.create_task_with_schedule(dto)


然后service拿到dto到下面的步骤
- DTO → Entity → repo
task = Task(
    user_id=dto.user_id,
    goal_id=dto.goal_id,
    title=dto.title,
    description=dto.description,
    is_active=dto.is_active,
    scoring_scheme_id=dto.scoring_scheme_id,
    scoring_scheme_json=dto.scoring_scheme_json,
    is_scoring_scheme_locked=dto.is_scoring_scheme_locked,
)

return self.task_repo.create(task)

降低耦合性
