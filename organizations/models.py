from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
import string
import random
import secrets
from safedelete.models import SafeDeleteModel, SOFT_DELETE
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from plio.cache import invalidate_cache_for_instances


class Organization(TenantMixin, SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

    name = models.CharField(max_length=255)
    shortcode = models.SlugField()
    api_key = models.CharField(null=True, max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    auto_create_schema = True

    class Meta:
        db_table = "organization"

    def _generate_random_secure_string(self, length=20):
        """Generates a cryptographically secure random string of given length"""
        return "".join(
            [
                secrets.choice(string.ascii_letters + string.digits)
                for _ in range(length)
            ]
        )

    def _generate_random_string(self, length=10):
        """Generates a random string of given length."""
        return "".join(random.choices(string.ascii_lowercase, k=length))

    def _generate_unique_schema_name(self):
        """Generates a unique schema name that adheres to database schema naming convention."""
        schema_name = self._generate_random_string()
        while Organization.objects.filter(schema_name=schema_name).exists():
            schema_name = self._generate_random_string()
        return schema_name

    def _generate_unique_api_key(self):
        """Generates a unique api_key."""
        api_key = self._generate_random_secure_string()
        while Organization.objects.filter(api_key=api_key).exists():
            api_key = self._generate_random_secure_string()
        return api_key

    def save(self, *args, **kwargs):
        """Organization save method. Before checking it creates a unique schema name if does not exist already."""
        if not self.schema_name:
            self.schema_name = self._generate_unique_schema_name()
        if not self.api_key:
            self.api_key = self._generate_unique_api_key()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.shortcode}: {self.name}"


class Domain(DomainMixin):
    pass


@receiver(post_save, sender=Organization)
@receiver(post_delete, sender=Organization)
def organization_update_cache(sender, instance, created, raw, **kwargs):
    # invalidate cache for users belonging to organization
    from users.models import User

    users = User.objects.filter(organizations__id=instance.id)
    invalidate_cache_for_instances(users)
