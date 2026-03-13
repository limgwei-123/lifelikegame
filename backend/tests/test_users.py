def test_me_without_token(client):
    response = client.get("users/me")
    assert response.status_code == 401


def test_me_success(client, auth_user):
    response = client.get("users/me", headers={
            "Authorization": f"Bearer {auth_user['access_token']}"
        })

    assert response.status_code == 200
    data = response.json()
    assert "email" in data

def test_search_by_id(client, auth_user):

    response = client.get(f"users/{auth_user['user_id']}", headers={
            "Authorization": f"Bearer {auth_user['access_token']}"
        })

    assert response.status_code == 200
    assert response.json()["id"] == auth_user['user_id']