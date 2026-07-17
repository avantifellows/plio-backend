import pytest
from django.conf import settings
from oauth2_provider.models import Application

from organizations.models import Organization
from plio import settings as base_settings
from users import views as user_views


def test_test_settings_are_safe_and_preserve_default_workspace():
    assert user_views.SMS_DRIVER is None
    assert settings.DEFAULT_TENANT_SHORTCODE == base_settings.DEFAULT_TENANT_SHORTCODE


def test_tenant_universe_seeds_oauth_application(db, request):
    if not all(
        item.get_closest_marker("integration") for item in request.session.items
    ):
        pytest.skip("OAuth session seed belongs to the integration lane")
    assert Application.objects.filter(name=settings.API_APPLICATION_NAME).exists()


def test_tenant_universe_seeds_the_configured_default_tenant(db):
    """No-header requests must resolve the configured default tenant row
    (shortcode -> public schema, as production seeds via `createtenant`), not
    fall through the middleware's unknown-tenant fallback."""
    if not settings.DEFAULT_TENANT_SHORTCODE:
        pytest.skip("no default tenant configured in this environment")
    assert Organization.objects.filter(
        shortcode=settings.DEFAULT_TENANT_SHORTCODE, schema_name="public"
    ).exists()
