def test_create_task(client, auth_headers,goal):

  task_response = client.post(
    f"/goals/{goal['id']}/tasks",
    headers=auth_headers,
    json={"title": "Learn AI"}
  )

  assert task_response.status_code in (200, 201)

def test_list_tasks_by_goal_id(client, auth_headers, goal):
  tasks_response = client.get(
    f"/goals/{goal['id']}/tasks",
    headers=auth_headers
  )

  assert tasks_response.status_code == 200

def test_list_tasks_by_user_id(client, auth_headers):
  tasks_response = client.get(
    "/tasks",
    headers=auth_headers
  )

  assert tasks_response.status_code == 200

def test_get_task_by_id(client, auth_headers, task):


  response = client.get(
        f"/tasks/{task['id']}",
        headers=auth_headers
    )

  assert response.status_code == 200



def test_update_task(client, auth_headers,task):

  response = client.post(
        f"/tasks/{task['id']}",
        headers=auth_headers,
        json={"title": "Learn AI2"}
    )

  assert response.status_code == 200

def test_delete_task(client, auth_headers, task):
  response = client.post(
      f"/tasks/{task['id']}/delete",
      headers=auth_headers,
  )

  assert response.status_code == 204
