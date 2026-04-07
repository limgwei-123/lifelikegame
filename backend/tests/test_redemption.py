def test_create_redemption(client, auth_headers,reward):

  redemption_response = client.post(
    "/redemptions",
    headers=auth_headers,
    json={
    "reward_id": reward['id'],
    }
    )

  assert redemption_response.status_code in (200, 201)


def test_list_redemptions_by_user_id(client, auth_headers):
  redemptions_response = client.get(
    "/redemptions",
    headers=auth_headers
  )

  assert redemptions_response.status_code == 200

def test_get_redemption_by_id(client, auth_headers, redemption):


  response = client.get(
        f"/redemptions/{redemption['id']}",
        headers=auth_headers
    )

  assert response.status_code == 200

