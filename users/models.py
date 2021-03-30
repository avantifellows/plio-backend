from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from organizations.models import Organization


class User(AbstractUser):
    email = models.CharField(max_length=255, null=True)
    phone = models.CharField(max_length=20, null=True)
    avatar_url = models.ImageField(upload_to="avatars/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "user"

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return "%d: %s" % (self.id, self.name)


class UserMeta(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    pincode = models.CharField(max_length=20, null=True)
    block = models.CharField(max_length=20, null=True)
    district = models.CharField(max_length=20, null=True)
    city = models.CharField(max_length=20, null=True)
    state = models.CharField(max_length=20, null=True)
    school = models.CharField(max_length=20, null=True)
    grade = models.CharField(max_length=20, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "user_meta"


class Role(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "role"


class OrganizationUser(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    organization = models.ForeignKey(Organization, on_delete=models.DO_NOTHING)
    is_owner = models.BooleanField(default=False)
    role_id = models.ForeignKey(Role, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "organization_user"
