import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_values(**overrides):
    values = {
        "APP_ENV": "production", "DEMO_MODE": False, "QRIS_DEMO_MODE": False,
        "ENABLE_DEMO_ENDPOINTS": False, "PUBLIC_REGISTRATION_ENABLED": False,
        "AUTO_SEED": False, "JWT_SECRET_KEY": "a" * 64,
        "POSTGRES_PASSWORD": "b" * 64, "PAYER_PSEUDONYM_KEY": "c" * 64,
        "TRUSTED_HOSTS": "qris.example.com", "BACKEND_CORS_ORIGINS": "https://qris.example.com",
    }
    values.update(overrides)
    return values


def test_production_rejects_placeholders_and_demo_features():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **production_values(JWT_SECRET_KEY="REPLACE_WITH_SECRET"))
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **production_values(DEMO_MODE=True))


def test_production_accepts_strong_explicit_configuration():
    settings = Settings(_env_file=None, **production_values())
    assert settings.APP_ENV == "production" and settings.demo_mode is False
