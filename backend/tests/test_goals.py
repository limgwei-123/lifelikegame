def test_create_goal(client, access_token):

  response = client.post(
    "/goals",
    headers={"Authorization": f"Bearer {access_token}"},
    json={"title": "Learn AI", "start_date":"2026-03-11"}
  )

  assert response.status_code in (200, 201)

def test_get_goal_by_id(client, test_user):
  login_response = client.post("/auth/login", json=test_user)
  token = login_response.json()["access_token"]

  me_response = client.get(
        "/profile/me",
        headers={"Authorization": f"Bearer {token}"}
    )

  user = me_response.json()

  goal_id = 1
  response = client.get(
    f"/goals/{goal_id}",
    headers={"Authorization": f"Bearer {token}"},
  )

  assert response.status_code == 200
  assert response.json()["user_id"] == user["id"]
