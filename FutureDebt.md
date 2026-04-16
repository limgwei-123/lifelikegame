- repo的naming要改的简洁一点 (done)
1） get_by_id 和 get by user_id 和 id都要保留

2） 未来要开dto
2） item pass进去repo最好是这样

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


3） 未来不要call别人的repo，service 调对方 service interface会比较好（如果要call 对方的router，会在微服务里面），包括ownership也一样，不要call repo，让他们带service进来（只是用service interface来限制）例如：
def get_owned_goal_or_raise(
    goal_service: GoalServiceInterface,
    goal_id: int,
    user_id: str,
):
    goal = goal_service.get_by_id_and_user_id(goal_id, user_id)

    if not goal:
        raise NotFoundError("Goal not found")

    return goal

4) 在workflow里面可以做成未来确保全部跑到了一次过commit（目前是分开可能遇到task create了，schedule没有create的问题）

5）要把dependencies部分改成build 和 get，只留depends在router(done)

6)那些model dump都要改掉，变成router就会给所有资料转成dto,然后不可以在service看到schemas这些字眼，最多dto（model dump拿掉了，只是没有用dto，用的service 那里create）



