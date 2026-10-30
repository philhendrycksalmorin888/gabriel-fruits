"""Authentication helpers for the Gabriel Fruit admin panel.

The repository stores only a PBKDF2 hash of the initial password, never the
plain-text password. Production deployments can override the hash/salt/rounds
through Streamlit secrets.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_PASSWORD_SALT = "gabriel-fruit-admin-v1"
DEFAULT_PASSWORD_ITERATIONS = 310_000
# Initial password configured by the project owner; only its derived hash is stored.
DEFAULT_PASSWORD_HASH = "a94902517148fc6ef62c2e38a61274b3385c4db0d2c4bf8bd9fc875ee24bbeb0"


@dataclass(frozen=True)
class AuthConfig:
    username: str = DEFAULT_ADMIN_USERNAME
    password_hash: str = DEFAULT_PASSWORD_HASH
    salt: str = DEFAULT_PASSWORD_SALT
    iterations: int = DEFAULT_PASSWORD_ITERATIONS


def hash_password(password: str, salt: str, iterations: int = DEFAULT_PASSWORD_ITERATIONS) -> str:
    """Return a PBKDF2-HMAC-SHA256 digest as hexadecimal text."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()


def verify_credentials(username: str, password: str, config: AuthConfig) -> bool:
    """Constant-time credential verification."""
    if not hmac.compare_digest(username.strip(), config.username):
        return False
    candidate = hash_password(password, config.salt, config.iterations)
    return hmac.compare_digest(candidate, config.password_hash)
