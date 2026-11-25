"""Persisted account behavior, credential revocation and rollback boundaries."""
from uuid import UUID, uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.auth import security
from app.users.models import User


@pytest.fixture
def http_client(client):
    # Reuse the active fixture's app/lifespan and DB overrides, but observe the
    # actual HTTP response instead of TestClient re-raising server exceptions.
    requester = TestClient(client.app, raise_server_exceptions=False)
    yield requester
    requester.close()


@pytest.fixture
def account(client, db):
    credentials = {"email": f"account-{uuid4()}@example.com", "password": "old-password-123"}
    signed = client.post('/auth/signup', json=credentials)
    assert signed.status_code == 201
    user_id = UUID(signed.json()['id'])
    token = client.post('/auth/login', json=credentials).json()['access_token']
    yield {"id": user_id, "credentials": credentials, "headers": {"Authorization": f"Bearer {token}"}}
    db.rollback()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()


def change(client, account, **changes):
    return client.post('/auth/change-password', headers=account['headers'], json={
        'current_password': account['credentials']['password'], 'new_password': 'new-password-456', **changes,
    })


def test_profile_update_persists_without_changing_identity_or_points(client, db, account):
    before = client.get('/users/me', headers=account['headers']).json()
    assert before.get('display_name') is None
    assert before.get('avatar_key') == 'leaf'
    response = client.patch('/users/me', headers=account['headers'], json={
        'display_name': '  小冒险家  ', 'avatar_key': 'sun', 'timezone': 'UTC',
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['display_name'] == '小冒险家' and result['avatar_key'] == 'sun' and result['timezone'] == 'UTC'
    for field in ('id', 'email', 'current_value'):
        assert result[field] == before[field]
    assert not {'password_hash', 'auth_version'} & result.keys()
    with Session(db.get_bind()) as reader:
        user = reader.get(User, account['id'])
        assert (user.display_name, user.avatar_key, user.timezone) == ('小冒险家', 'sun', 'UTC')
    assert client.get('/users/me', headers=account['headers']).json() == result
    assert client.get(f"/users/{account['id']}", headers=account['headers']).json() == result
    reset = client.patch('/users/me', headers=account['headers'], json={'display_name': None})
    assert reset.status_code == 200 and reset.json()['display_name'] is None
    assert reset.json()['avatar_key'] == 'sun'


@pytest.mark.parametrize('payload', [
    {}, {'display_name': ''}, {'display_name': '   '}, {'display_name': '名' * 31},
    {'avatar_key': 'https://example.com/avatar'}, {'avatar_key': None},
    {'timezone': 'not/a-zone'}, {'timezone': None}, {'timezone': '../UTC'},
    {'user_id': str(uuid4()), 'display_name': 'stolen'}, {'current_value': 999},
    {'email': 'different@example.com'}, {'auth_version': 0}, {'password_hash': 'bad'},
])
def test_invalid_profile_update_is_atomic(client, account, payload):
    before = client.get('/users/me', headers=account['headers']).json()
    response = client.patch('/users/me', headers=account['headers'], json=payload)
    assert response.status_code == 422, response.text
    assert client.get('/users/me', headers=account['headers']).json() == before


def test_profile_is_owned_and_requires_authentication(client, account, ownership_case):
    other = ownership_case['other']
    before = client.get('/users/me', headers=other['headers']).json()
    assert client.patch('/users/me', json={'display_name': 'intruder'}).status_code == 401
    assert client.patch('/users/me', headers=account['headers'],
                        json={'display_name': 'intruder', 'user_id': str(other['user'].id)}).status_code == 422
    assert client.patch(f"/users/{other['user'].id}", headers=account['headers'],
                        json={'display_name': 'intruder'}).status_code == 405
    assert client.get('/users/me', headers=other['headers']).json() == before


def test_password_change_verifies_old_password_and_revokes_all_old_tokens(client, db, account):
    second_token = client.post('/auth/login', json=account['credentials']).json()['access_token']
    wrong = change(client, account, current_password='incorrect-password')
    assert wrong.status_code == 403
    assert client.get('/users/me', headers=account['headers']).status_code == 200
    assert change(client, account).status_code == 204
    for headers in (account['headers'], {'Authorization': f'Bearer {second_token}'}):
        assert client.get('/users/me', headers=headers).status_code == 401
        assert client.patch('/users/me', headers=headers, json={'display_name': 'stale'}).status_code == 401
    assert client.post('/auth/login', json=account['credentials']).status_code == 401
    login = client.post('/auth/login', json={**account['credentials'], 'password': 'new-password-456'})
    assert login.status_code == 200
    assert client.get('/users/me', headers={'Authorization': f"Bearer {login.json()['access_token']}"}).status_code == 200
    with Session(db.get_bind()) as reader:
        user = reader.get(User, account['id'])
        assert user.auth_version == 1
        assert security.verify_password('new-password-456', user.password_hash)


@pytest.mark.parametrize('changes', [
    {'current_password': ''}, {'new_password': 'short'}, {'new_password': ' ' * 8},
    {'new_password': 'x' * 129}, {'new_password': None}, {'new_password': 12345678},
    {'user_id': str(uuid4())},
])
def test_bad_password_payload_does_not_change_credentials_or_echo_secrets(client, account, changes):
    response = change(client, account, **changes)
    assert response.status_code == 422, response.text
    assert 'old-password-123' not in response.text
    assert 'new-password-456' not in response.text
    assert 'x' * 129 not in response.text
    assert client.get('/users/me', headers=account['headers']).status_code == 200
    assert client.post('/auth/login', json=account['credentials']).status_code == 200


@pytest.mark.parametrize('version', [-1, True, '0', 0.5, None, 999])
def test_malformed_or_mismatched_token_versions_are_rejected(client, account, version):
    token = security.create_access_token(sub=str(account['id']))
    payload = security.decode_token(token)
    payload['auth_version'] = version
    token = jwt.encode(payload, security.JWT_SECRET, algorithm=security.JWT_ALG)
    assert client.get('/users/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_legacy_token_is_valid_only_until_password_changes(client, account):
    token = security.create_access_token(sub=str(account['id']))
    payload = security.decode_token(token)
    payload.pop('auth_version', None)
    legacy = jwt.encode(payload, security.JWT_SECRET, algorithm=security.JWT_ALG)
    headers = {'Authorization': f'Bearer {legacy}'}
    assert client.get('/users/me', headers=headers).status_code == 200
    assert change(client, account).status_code == 204
    assert client.get('/users/me', headers=headers).status_code == 401


def test_failed_password_commit_rolls_back_hash_and_revocation(client, http_client, db, account, monkeypatch):
    from app.core.unit_of_work import UnitOfWork
    with Session(db.get_bind()) as reader:
        before = reader.get(User, account['id']).password_hash
    with monkeypatch.context() as patch:
        patch.setattr(UnitOfWork, 'commit', lambda self: (_ for _ in ()).throw(RuntimeError('commit failed')))
        assert change(http_client, account).status_code == 500
    with Session(db.get_bind()) as reader:
        user = reader.get(User, account['id'])
        assert user.password_hash == before and user.auth_version == 0
    assert client.get('/users/me', headers=account['headers']).status_code == 200


def test_password_attempt_limit_is_per_user_and_keeps_credentials(client, account, ownership_case):
    for _ in range(5):
        assert change(client, account, current_password='incorrect-password').status_code == 403
    blocked = change(client, account)
    assert blocked.status_code == 429 and 1 <= int(blocked.headers['Retry-After']) <= 60
    # Another user has a separate allowance; use a real valid password hash.
    other = ownership_case['other']
    assert client.post('/auth/change-password', headers=other['headers'], json={
        'current_password': 'incorrect-password', 'new_password': 'new-password-456',
    }).status_code == 403
    assert client.get('/users/me', headers=account['headers']).status_code == 200


def test_stale_profile_writer_cannot_write_after_password_revocation(client, db, account):
    from app.users.service import UserService
    from app.users.repository import UserRepository
    from app.users.schemas import UpdateProfileRequest
    from app.errors.exception import AuthenticationError
    with Session(db.get_bind()) as stale_session:
        stale = stale_session.get(User, account['id'])
        expected_version = stale.auth_version
        assert change(client, account).status_code == 204
        with pytest.raises(AuthenticationError):
            UserService(UserRepository(stale_session)).update_profile(
                account['id'], expected_version, UpdateProfileRequest(display_name='stale'))
        stale_session.rollback()
    with Session(db.get_bind()) as reader:
        assert reader.get(User, account['id']).display_name is None


def test_concurrent_same_password_changes_only_accept_one_authenticated_version(db, account):
    from app.auth.service import AuthService
    from app.users.service import UserService
    from app.users.repository import UserRepository
    from app.errors.exception import AuthenticationError
    from app.core.unit_of_work import build_unit_of_work
    barrier = Barrier(2)
    def worker():
        with Session(db.get_bind()) as session:
            version = session.get(User, account['id']).auth_version
            barrier.wait(timeout=10)
            try:
                with build_unit_of_work(session).begin():
                    # Same password still revokes the old credentials. Checking
                    # only the password under the lock would accept both calls.
                    AuthService(UserService(UserRepository(session))).change_password(
                        account['id'], version, 'old-password-123', 'old-password-123')
                return 'changed'
            except AuthenticationError:
                return 'revoked'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: worker(), range(2)))
    assert sorted(results) == ['changed', 'revoked']
    with Session(db.get_bind()) as reader:
        assert reader.get(User, account['id']).auth_version == 1


def test_failed_profile_commit_does_not_persist_partial_changes(client, http_client, db, account, monkeypatch):
    from app.core.unit_of_work import UnitOfWork
    before = client.get('/users/me', headers=account['headers']).json()
    with monkeypatch.context() as patch:
        def fail_commit(self):
            raise RuntimeError('profile commit failed')
        patch.setattr(UnitOfWork, 'commit', fail_commit)
        response = http_client.patch('/users/me', headers=account['headers'],
                                     json={'display_name': 'Uncommitted', 'avatar_key': 'book', 'timezone': 'UTC'})
        assert response.status_code == 500
    assert client.get('/users/me', headers=account['headers']).json() == before


def test_changing_password_does_not_revoke_another_users_token(client, account, ownership_case):
    other = ownership_case['other']
    assert change(client, account).status_code == 204
    assert client.get('/users/me', headers=other['headers']).status_code == 200
    assert client.post('/auth/change-password', json={
        'current_password': 'old-password-123', 'new_password': 'new-password-456',
    }).status_code == 401
