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
            "text",
            "time",
            "meta",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["plio"] = PlioSerializer(instance.plio).data
        return response


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "item",
            "type",
            "options",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["item"] = ItemSerializer(instance.item).data
        return response
