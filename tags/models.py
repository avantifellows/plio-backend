from django.db import models
from django.utils.text import slugify
from safedelete.models import SafeDeleteModel, SOFT_DELETE


class Tag(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

    name = models.CharField(max_length=255)
    slug = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tag"

    def _generate_unique_slug(self):
        """Generates a unique slug based on the tag name."""
        unique_slug = slug = slugify(self.name)
        num = 1
        while Tag.objects.filter(slug=unique_slug).exists():
            unique_slug = "{}-{}".format(slug, num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        """Tag save method. Before checking it creates a unique tag slug if does not exist already."""
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)


class ModelHasTag(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.DO_NOTHING)
    model_type = models.CharField(max_length=255)
    model_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "model_has_tag"
