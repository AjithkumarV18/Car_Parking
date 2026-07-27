import pytest

from app.application.system.seed import SeedCredentials, validate_seed_credentials


def test_seed_credentials_reject_short_passwords_and_production() -> None:
    credentials = SeedCredentials("admin@example.test", "ValidPassword1!", "root@example.test", "AnotherPassword1!")
    validate_seed_credentials(credentials, is_production=False)
    with pytest.raises(ValueError, match="production"):
        validate_seed_credentials(credentials, is_production=True)
    with pytest.raises(ValueError, match="at least 12"):
        validate_seed_credentials(SeedCredentials("a@test", "short", "b@test", "AnotherPassword1!"), is_production=False)
    with pytest.raises(ValueError, match="must include"):
        validate_seed_credentials(SeedCredentials("a@test", "password-only", "b@test", "AnotherPassword1!"), is_production=False)
