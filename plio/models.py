from django.conf import settings
from django.db import models


class Video(models.Model):
    url = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "video"

    def __str__(self):
        return "%d: %s" % (self.id, self.title)


class Plio(models.Model):
    video = models.ForeignKey(Video, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=255)
    uuid = models.CharField(max_length=20)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING
    )
    failsafe_url = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=255, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "plio"

    def __str__(self):
        return "%d: %s" % (self.id, self.title)


class Item(models.Model):
    plio = models.ForeignKey(Plio, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=255)
    text = models.TextField()
    time = models.CharField(max_length=255)
    meta = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "item"


class Question(models.Model):
    item = models.ForeignKey(Item, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=255)
    options = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "question"
