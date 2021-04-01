from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.utils.text import slugify
import string
import random
from safedelete.models import SafeDeleteModel, SOFT_DELETE


class Organization(TenantMixin, SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

    name = models.CharField(max_length=255)
    shortcode = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    auto_create_schema = True

    class Meta:
        db_table = "organization"

    def _generate_random_string(self, length=10):
        """Generates a random string of given length."""
        return "".join(random.choices(string.ascii_lowercase, k=length))

    def _generate_unique_schema_name(self):
        """Generates a unique schema name that adheres to database schema naming convention."""
        schema_name = self._generate_random_string()
        while Organization.objects.filter(schema_name=schema_name).exists():
            schema_name = self._generate_random_string()
        return schema_name

    def save(self, *args, **kwargs):
        """Organization save method. Before checking it creates a unique schema name if does not exist already."""
        if not self.schema_name:
            self.schema_name = self._generate_unique_schema_name()
        super().save(*args, **kwargs)


class Domain(DomainMixin):
    pass
