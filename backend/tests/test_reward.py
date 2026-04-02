def test_create_reward(client, auth_headers):

  reward_response = client.post(
    "/rewards",
    headers=auth_headers,
    json={
    "title": "First Reward",
    "cost_points": 2
    }
    )

  assert reward_response.status_code in (200, 201)
  return reward_response.json()

def test_list_rewards_by_user_id(client, auth_headers):
  rewards_response = client.get(
    "/rewards",
    headers=auth_headers
  )

  assert rewards_response.status_code == 200

def test_get_reward_by_id(client, auth_headers, reward):


  response = client.get(
        f"/rewards/{reward['id']}",
        headers=auth_headers
    )

  assert response.status_code == 200



def test_update_reward(client, auth_headers,reward):

  response = client.post(
        f"/rewards/{reward['id']}",
        headers=auth_headers,
        json={
          "title": "Updated Reward",
          "cost_points": 1
          }
    )

  assert response.status_code == 200

def test_delete_reward(client, auth_headers, reward):
  response = client.post(
      f"/rewards/{reward['id']}/delete",
      headers=auth_headers,
  )

  assert response.status_code == 204
