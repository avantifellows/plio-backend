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
    watch_time = models.PositiveIntegerField(default=0)
    has_video_played = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "session"
        ordering = ["-id"]

    @property
    def last_session(self):
        """Get the session previous to this session for the same user-plio pair"""
        return (
            Session.objects.filter(plio_id=self.plio_id)
            .filter(user_id=self.user_id)
            .filter(id__lt=self.id)
            .first()
        )

    @property
    def last_event(self):
        """Returns the most recent event tied to a particular user-plio pair"""
        # find the most recent event for this session
        current_last_event = self.event_set.first()
        if current_last_event:
            return current_last_event

        # if there are no events in this session, find the most recent event in
        # the past sessions

        if not self.last_session:
            # this is the first session for the user-plio pair - no last event
            return None

        # either return the most recent event tied to the last session or
        # the last_event property of the last session in case no new events are
        # tied to the last session
        return self.last_session.event_set.first() or self.last_session.last_event


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
    PLAYED = "played"
    PAUSED = "paused"
    ENTER_FS = "enter_fullscreen"
    EXIT_FS = "exit_fullscreen"
    OPTION_SELECT = "option_selected"
    QUESTION_SKIP = "question_skipped"
    QUESTION_ANSWER = "question_answered"
    QUESTION_REVISE = "question_revised"
    QUESTION_PROCEED = "question_proceed"
    VIDEO_SEEKED = "video_seeked"
    TYPE_CHOICES = [
        (PLAYED, "Played"),
        (PAUSED, "Paused"),
        (ENTER_FS, "Enter Fullscreen"),
        (EXIT_FS, "Exit Fullscreen"),
        (OPTION_SELECT, "Option Selected"),
        (QUESTION_SKIP, "Question Skipped"),
        (QUESTION_ANSWER, "Question Answered"),
        (QUESTION_REVISE, "Question Revised"),
        (QUESTION_PROCEED, "Question Proceeded"),
        (VIDEO_SEEKED, "Video Seeked"),
    ]
    _safedelete_policy = SOFT_DELETE

    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=255, choices=TYPE_CHOICES)
    player_time = models.FloatField()
    details = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event"
        ordering = ["-id"]
