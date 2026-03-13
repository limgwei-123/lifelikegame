def test_create_goal(client, auth_headers):

  response = client.post(
    "/goals",
    headers=auth_headers,
    json={"title": "Learn AI", "start_date":"2026-03-11"}
  )

  assert response.status_code in (200, 201)


def test_list_goals(client, auth_headers):
  goals_response = client.get(
    "goals",
    headers=auth_headers
  )

  assert goals_response.status_code == 200

def test_get_goal_by_id(client, auth_headers, goal):


  response = client.get(
        f"/goals/{goal['id']}",
        headers=auth_headers
    )

  assert response.status_code == 200



def test_update_goal(client, auth_headers,goal):

  response = client.post(
        f"/goals/{goal['id']}",
        headers=auth_headers,
        json={"title": "Learn AI2", "start_date":"2026-03-11"}
    )

  assert response.status_code == 200

def test_delete_goal(client, auth_headers, goal):
  response = client.post(
      f"/goals/{goal['id']}/delete",
      headers=auth_headers,
  )

  assert response.status_code == 204
