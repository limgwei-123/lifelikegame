def test_me_without_token(client):
    response = client.get("auth/me")
    assert response.status_code == 401


def test_me_success(client, access_token):
    response = client.get("auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        })

    assert response.status_code == 200
    data = response.json()
    assert "email" in data