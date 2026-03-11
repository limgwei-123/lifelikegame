def test_create_goal(client, access_token):

  response = client.post(
    "/goals",
    headers={"Authorization": f"Bearer {access_token}"},
    json={"title": "Learn AI", "start_date":"2026-03-11"}
  )

  assert response.status_code in (200, 201)