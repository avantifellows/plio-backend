from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.utils.text import slugify
import string
import random


class Organization(TenantMixin):
    name = models.CharField(max_length=255)
    shortcode = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    auto_create_schema = True

    class Meta:
        db_table = "organization"

    def _generate_random_string(self):
        return "".join(random.choices(string.ascii_lowercase, k=10))

    def _generate_unique_schema_name(self):
        schema_name = self._generate_random_string()
        while Organization.objects.filter(schema_name=schema_name).exists():
            schema_name = self._generate_random_string()
        return schema_name

    def save(self, *args, **kwargs):
        if not self.schema_name:
            self.schema_name = self._generate_unique_schema_name()
        super().save(*args, **kwargs)


class Domain(DomainMixin):
    pass
