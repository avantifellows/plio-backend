from django.conf import settings
from django.db import models
from plio.models import Plio, Question
from experiments.models import Experiment
from safedelete.models import SafeDeleteModel, SOFT_DELETE


class Session(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    plio = models.ForeignKey(Plio, on_delete=models.DO_NOTHING)
    experiment = models.ForeignKey(Experiment, on_delete=models.DO_NOTHING, null=True)
    retention = models.TextField(default="")
    has_video_played = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "session"
        ordering = ["-id"]


class SessionAnswer(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING)
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING)
    answer = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "session_answer"


class Event(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=255)
    player_time = models.PositiveIntegerField()
    details = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event"
