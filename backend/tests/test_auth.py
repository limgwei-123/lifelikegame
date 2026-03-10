def test_signup_success(client):
    response = client.post("/auth/signup", json={
        'email': "newuser@test.com",
        'password': "password123"
    })

    assert response.status_code in (200, 201)


def test_login_success(client, test_user):
    response = client.post("/auth/login", json=test_user)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

