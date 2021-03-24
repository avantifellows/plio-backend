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
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
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


class Item(models.Model):
    plio = models.ForeignKey(Plio, on_delete=models.CASCADE)
    type = models.CharField(max_length=255)
    text = models.TextField()
    time = models.CharField(max_length=255)
    meta = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField()

    class Meta:
        db_table = "item"


class Question(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    type = models.CharField(max_length=255)
    options = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField()

    class Meta:
        db_table = "question"


class Experiment(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_test = models.BooleanField(default=False)
    type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "experiment"


class ExperimentPlio(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    plio = models.ForeignKey(Plio, on_delete=models.CASCADE)
    split_percentage = models.CharField(max_length=255)

    class Meta:
        db_table = "experiment_plio"


class Session(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plio = models.ForeignKey(Plio, on_delete=models.CASCADE)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    retention = models.TextField()
    has_video_played = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "session"


class SessionAnswer(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "session_answer"


class Event(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    type = models.CharField(max_length=255)
    player_time = models.PositiveIntegerField()
    details = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event"


class Tag(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tag"


class ModelHasTag(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    model_type = models.CharField(max_length=255)
    model_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "model_has_tag"