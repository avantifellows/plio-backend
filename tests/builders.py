from contextlib import contextmanager

from django_tenants.utils import schema_context


@contextmanager
def in_workspace(organization):
    with schema_context(organization.schema_name):
        yield
