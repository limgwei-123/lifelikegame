def login_user(client, email="test99@test.com", password="password123"):
  return client.post(
     "/auth/login",
     json = {
        "email": email,
        "password": password
     }
  )


def access_token(client, email="test99@test.com", password="password123"):

    response = login_user(client, email=email, password=password)
    return response.json()["access_token"]