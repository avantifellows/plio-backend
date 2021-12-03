from django.core.management.base import BaseCommand
import os
from organizations.models import Organization, Domain


class Command(BaseCommand):
    help = "Creates a default tenant based on .env"

    def handle(self, *args, **options):
        tenant_name = os.environ.get("DEFAULT_TENANT_NAME", "Plio")
        tenant_shortcode = os.environ.get("DEFAULT_TENANT_SHORTCODE", "plio")
        tenant_schema = "public"
        tenant_domain = os.environ.get("DEFAULT_TENANT_DOMAIN", "plio.in")

        tenant = Organization.objects.filter(schema_name=tenant_schema).first()
        if tenant:
            print("Tenant with public schema already exists. Skipping.")
        else:
            tenant = Organization.objects.create(
                schema_name=tenant_schema, name=tenant_name, shortcode=tenant_shortcode
            )
            Domain.objects.create(domain=tenant_domain, tenant=tenant, is_primary=True)
            print("Tenant created successfully!")
