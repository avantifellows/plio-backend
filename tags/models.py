from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tag"


class ModelHasTag(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.DO_NOTHING)
    model_type = models.CharField(max_length=255)
    model_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "model_has_tag"
