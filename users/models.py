from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from organizations.models import Organization
from safedelete.models import SafeDeleteModel, SafeDeleteManager, SOFT_DELETE
from .config import user_status_choices, org_admin_roles


class UserManager(SafeDeleteManager):
    def create_user(
        self,
        email=None,
        mobile=None,
        password=None,
        is_admin=False,
        is_staff=False,
        is_active=True,
        unique_id=None,
        auth_org=None,
    ):
        user = self.model()
        if email:
            user.email = self.normalize_email(email)
        user.mobile = mobile
        user.is_superuser = is_admin
        user.is_staff = is_staff
        user.is_active = is_active
        user.unique_id = unique_id
        user.auth_org = auth_org
        user.save(using=self._db)
        return user

    def create_superuser(self, email, mobile=None, password=None, **extra_fields):
        if not email:
            raise ValueError("User must have an email")
        if not password:
            raise ValueError("User must have a password")

        user = self.model(email=self.normalize_email(email))
        user.mobile = mobile
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save(using=self._db)
        return user

    @classmethod
    def normalize_email(cls, email):
        """
        Normalize the address by lowercasing the domain part of the email address.
        """
        email = email or ""
        try:
            email_name, domain_part = email.strip().rsplit("@", 1)
        except ValueError:
            pass
        else:
            email = "@".join([email_name, domain_part.lower()])
        return email

    def get_by_natural_key(self, email):
        return self.get(email=email)


class User(SafeDeleteModel, AbstractUser):
    _safedelete_policy = SOFT_DELETE

    username = None
    email = models.EmailField(max_length=255, null=True, unique=True)
    password = models.CharField(max_length=128, null=True)
    mobile = models.CharField(max_length=20, null=True)
    avatar_url = models.ImageField(upload_to="avatars/", null=True, blank=True)
    config = models.JSONField(null=True, default=dict)
    status = models.CharField(
        max_length=255, choices=user_status_choices, default="approved"
    )
    unique_id = models.CharField(max_length=255, null=True)
    auth_org = models.ForeignKey(
        Organization,
        on_delete=models.DO_NOTHING,
        related_name="auth_org",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    organizations = models.ManyToManyField(Organization, through="OrganizationUser")

    objects = UserManager()

    class Meta:
        db_table = "user"

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return "%d: %s" % (self.id, self.name)

    def get_role_for_organization(self, organization_id: int):
        """Returns the user's role within the organization provided (None if the user is not a part)"""
        organization_user = OrganizationUser.objects.filter(
            organization_id=organization_id, user_id=self.id
        ).first()
        if not organization_user:
            return None

        return organization_user.role

    def is_org_admin(self, organization_id: int, return_role: bool = False):
        """Whether the user has the privileges of an organisation's admin"""
        user_organization_role = self.get_role_for_organization(organization_id)
        has_org_admin_access = (
            user_organization_role is not None
            and user_organization_role.name in org_admin_roles
        )
        if not return_role:
            return has_org_admin_access

        return has_org_admin_access, user_organization_role


class UserMeta(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

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

    class Meta:
        db_table = "user_meta"


class Role(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "role"


class OrganizationUser(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    organization = models.ForeignKey(Organization, on_delete=models.DO_NOTHING)
    is_owner = models.BooleanField(default=False)
    role = models.ForeignKey(Role, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "organization_user"


class OneTimePassword(models.Model):
    mobile = models.CharField(max_length=20)
    otp = models.CharField(max_length=10)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "one_time_password"
