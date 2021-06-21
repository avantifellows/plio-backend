from django.db import connection
from django_tenants.middleware import TenantMainMiddleware
from django_tenants.utils import get_tenant_model
from plio.settings import DEFAULT_TENANT_SHORTCODE


class OrganizationTenantMiddleware(TenantMainMiddleware):
    """
    Sets connection to either public or tenant schema based on `ORGANIZATION` HTTP header value.
    """

    @staticmethod
    def get_organization_shortcode(request):
        """
        Returns the value of the `ORGANIZATION` HTTP header
        """
        org = request.META.get("HTTP_ORGANIZATION", DEFAULT_TENANT_SHORTCODE)
        if not org:
            return DEFAULT_TENANT_SHORTCODE

        return org

    def get_tenant(self, request):
        """
        Determines tenant by the value of the `ORGANIZATION` HTTP header.
        """
        # retrieve tenant model configured in settings.py
        tenant_model = get_tenant_model()

        organization_shortcode = self.get_organization_shortcode(request)
        return tenant_model.objects.filter(shortcode=organization_shortcode).first()

    def get_schema(self, request):
        """
        Determines the tenant schema name from the request
        """
        tenant = self.get_tenant(request)
        if tenant:
            return tenant.schema_name
        # as get_schema is being used when querying BigQuery datasets, we explicity need to mention `public`
        return "public"

    def process_request(self, request):
        """
        Switches connection to tenant schema if valid tenant.
        Otherwise keeps the connection with public schema.
        """
        # Connection needs first to be at the public schema, as this is where the tenant metadata is stored.
        connection.set_schema_to_public()

        # get the right tenant object based on request
        tenant = self.get_tenant(request)
        if tenant:
            # set connection to tenant's schema
            connection.set_tenant(tenant)
