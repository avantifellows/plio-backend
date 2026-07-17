"""Django admin smoke.

The Django admin is part of the surface the upgrade chain touches (auth,
templates, the admin app itself). These specs are a canary: the admin login
page renders, and at least one model changelist renders for a logged-in
superuser. Assertions observe the HTTP response the browser would receive --
never admin internals.
"""
from django.test import Client

from tests.factories import UserFactory


def test_admin_login_page_renders(db):
    # the login form is served to anyone hitting the admin unauthenticated
    response = Client().get("/admin/login/")

    assert response.status_code == 200


def test_admin_changelist_renders_for_superuser(db):
    superuser = UserFactory(is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(superuser)

    response = client.get("/admin/organizations/organization/")

    assert response.status_code == 200
