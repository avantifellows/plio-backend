from django.db import models
from django.utils.text import slugify


class Tag(models.Model):
    """
    description: User description

    List: sldfksdfjlk
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tag"

    def _generate_unique_slug(self):
        unique_slug = slug = slugify(self.name)
        num = 1
        while Tag.objects.filter(slug=unique_slug).exists():
            unique_slug = "{}-{}".format(slug, num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)


class ModelHasTag(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.DO_NOTHING)
    model_type = models.CharField(max_length=255)
    model_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "model_has_tag"
