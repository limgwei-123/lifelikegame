def test_create_task_with_schedule(client, auth_headers,goal,scoring_scheme):

  task_response = client.post(
    f"/workflows/goals/{goal['id']}/tasks",
    headers=auth_headers,
    json={
          "task": {
        "title": "string",
        "description": "string",
        "is_active": True,
        "scoring_scheme_id": scoring_scheme['id'],
        "is_scoring_scheme_locked": False
      }
      }
  )

  assert task_response.status_code in (200, 201)

def test_redemption_workflow(client, auth_headers, reward):
  redemption_response = client.post(
    f"/workflows/rewards/{reward['id']}/redeem",
    headers=auth_headers,
  )

  assert redemption_response.status_code in (200, 201)