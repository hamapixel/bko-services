"""Fast isolated tests. PostgreSQL specific tests will use production-style settings."""

from .settings import *  # noqa: F403,F401

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

PAYMENT_PROVIDER = "TEST"
PAYMENT_WEBHOOK_SECRET = "test-payment-webhook-secret"
