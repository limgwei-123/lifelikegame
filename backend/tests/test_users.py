def test_me_without_token(client):
    response = client.get("users/me")
    assert response.status_code == 401


def test_me_success(client, access_token):
    response = client.get("users/me", headers={
            "Authorization": f"Bearer {access_token}"
        })

    assert response.status_code == 200
    data = response.json()
    assert "email" in data

def test_search_by_id(client, access_token,test_user):
    me_response = client.get("users/me", headers={
            "Authorization": f"Bearer {access_token}"
        })

    assert me_response.status_code == 200
    me_data = me_response.json()
    user_id = me_data['id']

    response = client.get(f"users/{user_id}", headers={
            "Authorization": f"Bearer {access_token}"
        })
    assert response.status_code == 200
    assert response.json()["id"] == user_id