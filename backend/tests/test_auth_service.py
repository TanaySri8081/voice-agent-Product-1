from datetime import timedelta

from backend.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_token,
    hash_token,
)


def test_password_hash_roundtrip():
    hashed = get_password_hash("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_roundtrip():
    token = create_access_token({"sub": "abc", "role": "doctor"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "abc"
    assert payload["role"] == "doctor"


def test_jwt_invalid_returns_none():
    assert decode_access_token("not.a.jwt") is None


def test_jwt_expired_returns_none():
    token = create_access_token({"sub": "x"}, expires_delta=timedelta(seconds=-1))
    assert decode_access_token(token) is None


def test_reset_token_helpers():
    a = generate_token()
    b = generate_token()
    assert a != b
    assert len(a) > 20
    # hashing is deterministic, sha256 hex (64 chars), and not the raw token
    assert hash_token("foo") == hash_token("foo")
    assert hash_token("foo") != hash_token("bar")
    assert hash_token("foo") != "foo"
    assert len(hash_token("foo")) == 64
