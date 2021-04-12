from django.conf import settings
from django.db import connection
from django_tenants.middleware import TenantMainMiddleware
from django_tenants.utils import get_public_schema_name, get_tenant_model


class OrganizationTenantMiddleware(TenantMainMiddleware):
    """
    Determines tenant by the value of the ``ORGANIZATION`` HTTP header.
    """

    def get_tenant(self, tenant_model, hostname, request):
        organization_shortcode = request.META.get(
            "HTTP_ORGANIZATION", get_public_schema_name()
        )
        return tenant_model.objects.filter(shortcode=organization_shortcode).first()

    def process_request(self, request):
        # Connection needs first to be at the public schema, as this is where the tenant metadata is stored.
        connection.set_schema_to_public()
        hostname = self.hostname_from_request(request)

        tenant_model = get_tenant_model()
        tenant = self.get_tenant(tenant_model, hostname, request)
        if tenant:
            connection.set_tenant(tenant)
