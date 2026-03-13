def test_create_goal(client, auth_user):

  response = client.post(
    "/goals",
    headers={"Authorization": f"Bearer {auth_user['access_token']}"},
    json={"title": "Learn AI", "start_date":"2026-03-11"}
  )

  assert response.status_code in (200, 201)

def test_get_goal_by_id(client, auth_user):

  create = client.post(
    "/goals",
    json={"title": "Learn AI", "start_date":"2026-03-11"},
    headers={"Authorization": f"Bearer {auth_user['access_token']}"}
  )

  goal = create.json()
  goal_id = goal["id"]

  response = client.get(
        f"/goals/{goal_id}",
        headers={"Authorization": f"Bearer {auth_user['access_token']}"}
    )

  assert response.status_code == 200
  assert response.json()["user_id"] == auth_user["user_id"]
