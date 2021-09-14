from rest_framework import serializers
from plio.models import Video, Plio, Item, Question, Image
from users.models import User
from users.serializers import UserSerializer
from django.core.cache import cache
from plio.cache import get_cache_key


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = [
            "id",
            "url",
            "alt_text",
            "created_at",
            "updated_at",
        ]


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = [
            "id",
            "url",
            "title",
            "duration",
            "created_at",
            "updated_at",
        ]


class PlioSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Plio
        fields = [
            "id",
            "name",
            "uuid",
            "failsafe_url",
            "status",
            "is_public",
            "config",
            "created_by",
            "video",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid"]

    def to_representation(self, instance):
        # check if a cached version exists and if it does, return it as the response
        cache_key = get_cache_key(instance)
        cachedResponse = cache.get(cache_key)
        if cachedResponse:
            return cachedResponse

        response = super().to_representation(instance)
        response["video"] = VideoSerializer(instance.video).data
        response["created_by"] = UserSerializer(instance.created_by).data

        cache.set(cache_key, response)  # set a cached version
        return response


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            "id",
            "plio",
            "type",
            "time",
            "meta",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        response = super().to_representation(instance)
        # add the question details to the item response if it exists
        if instance.type == "question":
            question = instance.question_set.all().first()
            if question:
                response["details"] = QuestionSerializer(question).data
            else:
                response["details"] = {}
        return response


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "item",
            "text",
            "type",
            "options",
            "correct_answer",
            "image",
            "has_char_limit",
            "max_char_limit",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        response = super().to_representation(instance)
        if instance.image:
            response["image"] = ImageSerializer(instance.image).data
        return response
