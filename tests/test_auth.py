from auth import AuthConfig, hash_password, verify_credentials


def test_verify_credentials_with_custom_config():
    salt = "unit-test-salt"
    config = AuthConfig(
        username="admin",
        password_hash=hash_password("test-password", salt, 20_000),
        salt=salt,
        iterations=20_000,
    )
    assert verify_credentials("admin", "test-password", config)
    assert not verify_credentials("admin", "wrong-password", config)
    assert not verify_credentials("other-user", "test-password", config)


def test_hash_is_deterministic():
    assert hash_password("abc", "salt", 10_000) == hash_password("abc", "salt", 10_000)
