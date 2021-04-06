from rest_framework import serializers
from plio.models import Video, Plio, Item, Question
from users.serializers import UserSerializer


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
        response = super().to_representation(instance)
        response["video"] = VideoSerializer(instance.video).data
        response["created_by"] = UserSerializer(instance.created_by).data
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
        if instance.type == "question":
            # add the question details to the item response
            response["details"] = QuestionSerializer(
                instance.question_set.all()[0]
            ).data
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
            "created_at",
            "updated_at",
        ]
