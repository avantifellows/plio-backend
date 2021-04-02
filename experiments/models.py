from django.conf import settings
from django.db import models
from plio.models import Plio
from safedelete.models import SafeDeleteModel, SOFT_DELETE


class Experiment(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

    name = models.CharField(max_length=255)
    description = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING
    )
    is_test = models.BooleanField(default=False)
    type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "experiment"


class ExperimentPlio(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.DO_NOTHING)
    plio = models.ForeignKey(Plio, on_delete=models.DO_NOTHING)
    split_percentage = models.CharField(max_length=255)

    class Meta:
        db_table = "experiment_plio"
