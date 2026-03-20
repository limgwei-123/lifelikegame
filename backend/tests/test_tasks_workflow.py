def test_create_task(client, auth_headers,goal):

  task_response = client.post(
    f"/goals/{goal['id']}/tasks",
    headers=auth_headers,
    json={
      "title": "Learn AI",
      "schedule": {
        "schedule_type": "daily",
        "schedule_value_json": {
            "additionalProp1": {}
        },
      }
      }
  )



  assert task_response.status_code in (200, 201)