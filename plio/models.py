from django.conf import settings
from django.db import models


class Video(models.Model):
    url = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "video"


class Plio(models.Model):
    video_id = models.ForeignKey(Video, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    uuid = models.CharField(max_length=20)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    failsafe_url = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=255, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField()

    class Meta:
        db_table = "plio"
