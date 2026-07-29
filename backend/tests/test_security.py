from app.auth import security

TEST_JWT_SECRET = "unit-test-jwt-secret"
TEST_JWT_ALGORITHM = "HS256"

def test_access_token_can_be_encoded_and_decoded(monkeypatch):
    monkeypatch.setattr(
        security,
        "JWT_SECRET",
        TEST_JWT_SECRET,
    )
    monkeypatch.setattr(
        security,
        "JWT_ALG",
        TEST_JWT_ALGORITHM,
    )

    token = security.create_access_token(
        sub="test-user-id",
        expire_minutes=15,
    )

    payload = security.decode_token(token)

    assert payload["sub"] == "test-user-id"
    assert isinstance(payload["iat"], int)
    assert isinstance(payload["exp"], int)
    assert payload["exp"] - payload["iat"] == 15 * 60


def test_access_token_uses_configured_default_expiry(monkeypatch):
    monkeypatch.setattr(
        security,
        "JWT_SECRET",
        TEST_JWT_SECRET,
    )
    monkeypatch.setattr(
        security,
        "JWT_ALG",
        TEST_JWT_ALGORITHM,
    )
    monkeypatch.setattr(
        security,
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        30,
    )

    token = security.create_access_token(sub="test-user-id")
    payload = security.decode_token(token)

    assert payload["exp"] - payload["iat"] == 30 * 60