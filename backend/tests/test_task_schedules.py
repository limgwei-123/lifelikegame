def test_create_task_schedule(client, auth_headers,task):

  task_response = client.post(
    f"/tasks/{task['id']}/task_schedules",
    json={
        "schedule_type": "daily",
        "schedule_value_json": {
            "additionalProp1": {}
        },
    },
    headers=auth_headers,
  )

  print("Task Response:",task_response)
  assert task_response.status_code in (200, 201)

def test_list_task_schedules_by_task_id(client, auth_headers, task):
  task_schedules_response = client.get(
    f"/tasks/{task['id']}/task_schedules",
    headers=auth_headers
  )

  assert task_schedules_response.status_code == 200

def test_list_task_schedules_by_user_id(client, auth_headers):
  task_schedules_response = client.get(
    "/task_schedules",
    headers=auth_headers
  )

  assert task_schedules_response.status_code == 200

def test_get_task_schedule_by_id(client, auth_headers, task_schedule):


  response = client.get(
        f"/task_schedules/{task_schedule['id']}",
        headers=auth_headers
    )

  assert response.status_code == 200



def test_update_task_schedule(client, auth_headers,task_schedule):

  response = client.post(
        f"/task_schedules/{task_schedule['id']}",
        headers=auth_headers,
        json={
          "schedule_type": "daily",
          "schedule_value_json": {
            "additionalProp1": {}
          },
        }
    )

  assert response.status_code == 200

def test_delete_task_schedule(client, auth_headers, task_schedule):
  response = client.post(
      f"/task_schedules/{task_schedule['id']}/delete",
      headers=auth_headers,
  )

  assert response.status_code == 204
