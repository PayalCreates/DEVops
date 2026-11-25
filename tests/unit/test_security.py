"""Unit tests: password hashing and JWT handling."""

import time

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_salted_and_verifies():
    h1, h2 = hash_password("Secret123"), hash_password("Secret123")
    assert h1 != h2  # random salt
    assert verify_password("Secret123", h1)
    assert not verify_password("secret123", h1)


def test_verify_handles_garbage_hash():
    assert verify_password("x", "not-a-bcrypt-hash") is False


def test_token_roundtrip_contains_claims():
    token = create_access_token("42", "admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert payload["exp"] > payload["iat"]


def test_expired_token_rejected():
    token = create_access_token("1", "user", expires_minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_token_rejected():
    token = create_access_token("1", "user")
    forged = jwt.encode({"sub": "1", "role": "admin", "iat": int(time.time()),
                         "exp": int(time.time()) + 600, "iss": "DevSecOps360"},
                        "attacker-key-that-is-long-enough-000000000", algorithm="HS256")
    assert decode_access_token(token)["role"] == "user"
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)


def test_none_algorithm_rejected():
    unsigned = jwt.encode({"sub": "1", "exp": int(time.time()) + 60, "iat": 0,
                           "iss": "DevSecOps360"}, key=None, algorithm="none")
    with pytest.raises(jwt.InvalidAlgorithmError):
        decode_access_token(unsigned)
