from django.conf import settings
from django.db import connection
from django_tenants.middleware import TenantMainMiddleware
from django_tenants.utils import get_public_schema_name, get_tenant_model


class OrganizationTenantMiddleware(TenantMainMiddleware):
    """
    Sets connection to either public or tenant schema based on `ORGANIZATION` HTTP header value.
    """

    def get_tenant(self, tenant_model, request):
        """
        Determines tenant by the value of the `ORGANIZATION` HTTP header.
        """
        organization_shortcode = request.META.get(
            "HTTP_ORGANIZATION", get_public_schema_name()
        )
        return tenant_model.objects.filter(shortcode=organization_shortcode).first()

    def process_request(self, request):
        """
        Switches connection to tenant schema if valid tenant. Otherwise keeps the connection with public schema.
        """
        # Connection needs first to be at the public schema, as this is where the tenant metadata is stored.
        connection.set_schema_to_public()

        # retrieve tenant model configured in settings.py
        tenant_model = get_tenant_model()

        # get the right tenant object based on request
        tenant = self.get_tenant(tenant_model, request)
        if tenant:
            # set connection to tenant's schema
            connection.set_tenant(tenant)
