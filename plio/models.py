from django.conf import settings
from django.db import models
import string
import random
import os
from safedelete.models import SafeDeleteModel, SOFT_DELETE, SOFT_DELETE_CASCADE
from plio.config import plio_status_choices, item_type_choices, question_type_choices


class Image(SafeDeleteModel):
    _safedelte_policy = SOFT_DELETE

    url = models.ImageField("Image", upload_to="images")
    alt_text = models.CharField(max_length=255, default="Image")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "image"

    def __str__(self):
        return f"{self.id}: {self.url}"

    def _generate_random_string(self, length=10):
        """Generates a random string of given length."""
        return "".join(random.choices(string.ascii_lowercase, k=length))

    def _generate_unique_uuid(self):
        """Generates a unique file name for the image being uploaded."""
        new_file_name = self._generate_random_string()

        while Image.objects.filter(url__icontains=new_file_name).exists():
            new_file_name = self._generate_random_string()
        return new_file_name

    def save(self, *args, **kwargs):
        """Image save method. Before uploading, it creates a unique file name for the image."""
        # to avoid setting a new name every time the model is saved
        if not self.id:
            dir_name = os.path.dirname(self.url.name)
            file_name = "".join(
                [self._generate_unique_uuid(), os.path.splitext(self.url.name)[1]]
            )
            self.url.name = os.path.join(dir_name, file_name)
        super().save(*args, **kwargs)


class Video(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE

    url = models.CharField(max_length=255)
    title = models.CharField(max_length=255, null=True)
    duration = models.FloatField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "video"

    def __str__(self):
        return "%d: %s" % (self.id, self.title)


class Plio(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    video = models.ForeignKey(Video, null=True, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=255, blank=True, default="")
    uuid = models.SlugField(unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING
    )
    failsafe_url = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=255, choices=plio_status_choices, default="draft"
    )
    is_public = models.BooleanField(default=True)
    config = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plio"
        ordering = ["-updated_at"]

    def __str__(self):
        return "%d: %s" % (self.id, self.name)

    def _generate_random_string(self, length=10):
        """Generates a random string of given length."""
        return "".join(random.choices(string.ascii_lowercase, k=length))

    def _generate_unique_uuid(self):
        """Generates a unique uuid for the plio."""
        uuid = self._generate_random_string()
        while Plio.objects.filter(uuid=uuid).exists():
            uuid = self._generate_random_string()
        return uuid

    def save(self, *args, **kwargs):
        """Plio save method. Before checking it creates a unique uuid for the plio if does not exist already."""
        if not self.uuid:
            self.uuid = self._generate_unique_uuid()
        super().save(*args, **kwargs)


class Item(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    plio = models.ForeignKey(Plio, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=255, choices=item_type_choices, default="question"
    )
    time = models.FloatField()
    meta = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "item"
        ordering = ["time"]

    def __str__(self):
        return "%d: %s - %s" % (self.id, self.plio.name, self.type)


class Question(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    image = models.ForeignKey(Image, null=True, on_delete=models.DO_NOTHING)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=255, choices=question_type_choices, default="mcq"
    )
    text = models.TextField(blank=True, default="")
    options = models.JSONField(null=True)
    option_images = models.JSONField(null=True, blank=True)  # This is an object where keys are indices in the options array and values are image IDs
    correct_answer = models.JSONField(null=True)
    survey = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    has_char_limit = models.BooleanField(default=False)
    max_char_limit = models.FloatField(null=True)

    class Meta:
        db_table = "question"
        ordering = ["item__time"]
