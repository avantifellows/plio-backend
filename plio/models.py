from django.conf import settings
from django.db import models
import string
import random
from safedelete.models import SafeDeleteModel, SOFT_DELETE


class Video(SafeDeleteModel):
    url = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "video"

    def __str__(self):
        return "%d: %s" % (self.id, self.title)


class Plio(SafeDeleteModel):
    video = models.ForeignKey(Video, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=255)
    uuid = models.SlugField(unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING
    )
    failsafe_url = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=255, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plio"

    def __str__(self):
        return "%d: %s" % (self.id, self.name)

    def _generate_random_string(self, length=10):
        return "".join(random.choices(string.ascii_lowercase, k=length))

    def _generate_unique_uuid(self):
        uuid = self._generate_random_string()
        while Plio.objects.filter(uuid=uuid).exists():
            uuid = self._generate_random_string()
        return uuid

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = self._generate_unique_uuid()
        super().save(*args, **kwargs)


class Item(SafeDeleteModel):
    plio = models.ForeignKey(Plio, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=255)
    text = models.TextField()
    time = models.CharField(max_length=255)
    meta = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "item"

    def __str__(self):
        return "%d: %s - %s" % (self.id, self.plio.name, self.text)


class Question(SafeDeleteModel):
    item = models.ForeignKey(Item, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=255)
    options = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "question"
