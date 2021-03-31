from django.conf import settings
from django.db import models
from plio.models import Plio, Question
from experiments.models import Experiment


class Session(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    plio = models.ForeignKey(Plio, on_delete=models.DO_NOTHING)
    experiment = models.ForeignKey(Experiment, on_delete=models.DO_NOTHING)
    retention = models.TextField()
    has_video_played = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "session"


class SessionAnswer(models.Model):
    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING)
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING)
    answer = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "session_answer"


class Event(models.Model):
    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=255)
    player_time = models.PositiveIntegerField()
    details = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "event"
