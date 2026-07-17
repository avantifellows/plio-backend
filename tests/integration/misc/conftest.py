"""Fixtures for the misc integration lane.

The websocket canary is the one journey in the whole suite that needs *real*
commits: the channels consumer runs in its own thread and can only see rows the
test has committed, so it cannot use the suite's default transaction-rollback
isolation. ``slow_lane_db`` gives it committed writes and cleans up by
truncation instead.

Truncation interacts badly with this project's django-tenants layout, and
untangling that is part of this slice. The shared apps (plio, entries, ...) keep
their tables in the *public* schema too, so those tables carry foreign keys to
one another; pytest-django's stock ``transactional_db`` teardown issues a plain
``TRUNCATE`` with no ``CASCADE`` and Postgres rejects it. We therefore run the
flush ourselves with ``allow_cascade=True``. That flush also removes the
per-worker tenant universe ``django_db_setup`` seeds once per run -- the
org-a/org-b organizations, the role rows, and the oauth2 Application -- which the
rollback-based specs that run afterwards depend on, so ``slow_lane_db`` rebuilds
it before yielding control back.
"""
import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from oauth2_provider.models import Application

from organizations.models import Organization
from users.models import Role


def _ensure_api_application():
    Application.objects.get_or_create(
        name=settings.API_APPLICATION_NAME,
        defaults={
            "redirect_uris": "",
            "client_type": Application.CLIENT_CONFIDENTIAL,
            "authorization_grant_type": Application.GRANT_AUTHORIZATION_CODE,
        },
    )


def _rebuild_tenant_universe(organizations):
    """Re-seed the universe rows a slow_lane flush wipes.

    Roles and the oauth2 Application are looked up by natural key everywhere, so
    re-seeding them with fresh primary keys is enough. The organizations must
    keep their *original* primary keys -- the session-scoped ``org_a``/``org_b``
    fixtures cache their instances and later specs foreign-key to those cached
    ids -- so each org row is re-inserted with ``force_insert`` (its schema
    already exists, so ``TenantMixin`` does not try to re-provision it).
    """
    connection.set_schema_to_public()
    for role in settings.DEFAULT_ROLES:
        Role.objects.get_or_create(name=role["name"])
    if settings.DEFAULT_TENANT_SHORTCODE:
        # the default-tenant row (shortcode -> public schema) is looked up by
        # shortcode, so a fresh primary key is fine -- mirror the session seed
        Organization.objects.get_or_create(
            shortcode=settings.DEFAULT_TENANT_SHORTCODE,
            defaults={"name": "Personal workspace", "schema_name": "public"},
        )
    for organization in organizations:
        if not Organization.objects.filter(pk=organization.pk).exists():
            organization.save(force_insert=True)
    _ensure_api_application()


@pytest.fixture
def slow_lane_db(django_db_setup, django_db_blocker, org_a, org_b):
    """Commit-capable DB access for a slow_lane test, cleaned up by truncation.

    Writes are committed (no wrapping transaction) so a consumer running in its
    own thread can see them; teardown truncates the public schema with CASCADE
    and rebuilds the tenant universe so no state leaks into later rollback-based
    tests.
    """
    with django_db_blocker.unblock():
        connection.set_schema_to_public()
        try:
            yield
        finally:
            call_command(
                "flush",
                verbosity=0,
                interactive=False,
                allow_cascade=True,
                reset_sequences=False,
            )
            _rebuild_tenant_universe([org_a, org_b])
            connection.set_schema_to_public()
