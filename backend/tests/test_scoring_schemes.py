def test_create_scoring_scheme(client, auth_headers):

  response = client.post(
    "/scoring_schemes",
    headers=auth_headers,
    json={
  "title": "normal",
  "levels_json": {
    "additionalProp1": 0,
    "additionalProp2": 0,
    "additionalProp3": 0
      }
    }
  )

  assert response.status_code in (200, 201)


def test_list_scoring_schemes(client, auth_headers):
  scoring_schemes_response = client.get(
    "/scoring_schemes",
    headers=auth_headers
  )

  assert scoring_schemes_response.status_code == 200

def test_get_scoring_scheme_by_id(client, auth_headers, scoring_scheme):


  response = client.get(
        f"/scoring_schemes/{scoring_scheme['id']}",
        headers=auth_headers
    )

  assert response.status_code == 200



def test_update_scoring_scheme(client, auth_headers,scoring_scheme):

  response = client.post(
        f"/scoring_schemes/{scoring_scheme['id']}",
        headers=auth_headers,
        json={
        "title": "normal",
        "levels_json": {
          "additionalProp1": 0,
          "additionalProp2": 0,
          "additionalProp3": 0
            }
          }
    )

  assert response.status_code == 200

def test_delete_scoring_scheme(client, auth_headers, scoring_scheme):
  response = client.post(
      f"/scoring_schemes/{scoring_scheme['id']}/delete",
      headers=auth_headers,
  )

  assert response.status_code == 204
