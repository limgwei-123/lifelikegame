def test_create_point_ledger(client, auth_headers):

  response = client.post(
    "/point_ledgers",
    headers=auth_headers,
    json={
  "event_at": "2026-03-27",
  "delta": 0,
  "entry_type": "string",
  "source_type": "string",
  "source_id": 0,
  "description": "string"
}
  )

  assert response.status_code in (200, 201)


def test_list_point_ledger(client, auth_headers):
  scoring_schemes_response = client.get(
    "/point_ledgers",
    headers=auth_headers
  )

  assert scoring_schemes_response.status_code == 200

def test_get_balance(client, auth_headers):

  scoring_schemes_response = client.get(
    "/point_ledgers/balance",
    headers=auth_headers
  )

  assert scoring_schemes_response.status_code == 200
