from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from organizations.models import Organization
from safedelete.models import SafeDeleteModel, SafeDeleteManager, SOFT_DELETE


class UserManager(SafeDeleteManager):
    def create_user(
        self,
        email,
        phone=None,
        password=None,
        is_admin=False,
        is_staff=False,
        is_active=True,
    ):
        if not email:
            raise ValueError("User must have an email")

        user = self.model(email=self.normalize_email(email))
        user.phone = phone
        user.is_superuser = is_admin
        user.is_staff = is_staff
        user.is_active = is_active
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone=None, password=None, **extra_fields):
        if not email:
            raise ValueError("User must have an email")
        if not password:
            raise ValueError("User must have a password")

        user = self.model(email=self.normalize_email(email))
        user.phone = phone
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
    phone = models.CharField(max_length=20, null=True)
    avatar_url = models.ImageField(upload_to="avatars/", null=True, blank=True)
    config = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "user"

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return "%d: %s" % (self.id, self.name)


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
    role_id = models.ForeignKey(Role, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "organization_user"
