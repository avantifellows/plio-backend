from django.conf import settings
from django.db import models
from plio.models import Plio


class Experiment(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_test = models.BooleanField(default=False)
    type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "experiment"


class ExperimentPlio(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    plio = models.ForeignKey(Plio, on_delete=models.CASCADE)
    split_percentage = models.CharField(max_length=255)

    class Meta:
        db_table = "experiment_plio"
