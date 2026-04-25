from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    safe_decode_token,
    verify_password,
)


def test_hash_password_and_verify() -> None:
    plain_password = "StrongPass123!"
    hashed_password = hash_password(plain_password)

    assert hashed_password != plain_password
    assert verify_password(plain_password, hashed_password) is True
    assert verify_password("wrong-password", hashed_password) is False


def test_create_and_decode_access_token() -> None:
    token = create_access_token(subject="user@example.com")
    payload = decode_token(token)

    assert payload["sub"] == "user@example.com"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_safe_decode_invalid_token_returns_none() -> None:
    assert safe_decode_token("this-is-not-a-token") is None
