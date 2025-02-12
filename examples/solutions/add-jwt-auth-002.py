"""Reference solution for task add-jwt-auth-002.

This file shows the two new files that a correct solution must produce:
  1. app/auth.py       – token validation logic
  2. tests/test_auth.py – four-scenario test suite

Usage notes
-----------
- Uses PyJWT >= 2.0 (encode returns str, not bytes).
- JWT_SECRET read from environment variable; falls back to a dev default.
- The Bearer prefix check is case-insensitive (covers hidden edge case hec-3).
"""

# ════════════════════════════════════════════════════════════════════════════
# app/auth.py
# ════════════════════════════════════════════════════════════════════════════

APP_AUTH_PY = '''
"""JWT authentication helpers for the Flask API."""

from __future__ import annotations

import os
from functools import wraps
from typing import Callable

import jwt
from flask import jsonify, request

JWT_ALGORITHM = "HS256"
_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")


class AuthError(Exception):
    """Raised when token validation fails."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


def verify_token(token: str) -> dict:
    """Decode and verify a JWT bearer token.

    Args:
        token: Raw JWT string (without the 'Bearer ' prefix).

    Returns:
        The decoded payload dict.

    Raises:
        AuthError: On any validation failure (expired, tampered, malformed).
    """
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired.")
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"Invalid token: {exc}")


def require_auth(f: Callable) -> Callable:
    """Flask route decorator that enforces JWT authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return jsonify({"error": "Missing or malformed Authorization header."}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            verify_token(token)
        except AuthError as exc:
            return jsonify({"error": str(exc)}), exc.status_code

        return f(*args, **kwargs)

    return decorated
'''


# ════════════════════════════════════════════════════════════════════════════
# tests/test_auth.py
# ════════════════════════════════════════════════════════════════════════════

TESTS_TEST_AUTH_PY = '''
"""Tests for JWT authentication on the /api/users endpoint."""

from __future__ import annotations

import time
import os

import jwt
import pytest

JWT_ALGORITHM = "HS256"
_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_token(payload: dict, secret: str = _SECRET) -> str:
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


# ── Scenario 1: valid token ──────────────────────────────────────────────────

def test_valid_token_returns_200(client):
    token = _make_token({"sub": "testuser", "exp": int(time.time()) + 3600})
    resp = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


# ── Scenario 2: missing token ────────────────────────────────────────────────

def test_missing_token_returns_401(client):
    resp = client.get("/api/users")
    assert resp.status_code == 401
    data = resp.get_json()
    assert "error" in data


# ── Scenario 3: expired token ────────────────────────────────────────────────

def test_expired_token_returns_401(client):
    token = _make_token({"sub": "testuser", "exp": int(time.time()) - 3600})
    resp = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "expired" in resp.get_json()["error"].lower()


# ── Scenario 4: tampered / wrong secret ──────────────────────────────────────

def test_tampered_token_returns_401(client):
    token = _make_token({"sub": "testuser"}, secret="wrong-secret")
    resp = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# ── Hidden edge case: case-insensitive Bearer prefix ─────────────────────────

def test_lowercase_bearer_prefix_accepted(client):
    token = _make_token({"sub": "testuser", "exp": int(time.time()) + 3600})
    resp = client.get("/api/users", headers={"Authorization": f"bearer {token}"})
    assert resp.status_code == 200
'''


if __name__ == "__main__":
    print("=== app/auth.py ===")
    print(APP_AUTH_PY)
    print("\n=== tests/test_auth.py ===")
    print(TESTS_TEST_AUTH_PY)
