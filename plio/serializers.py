from rest_framework import serializers
from plio.models import Video, Plio


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

    def create(self, validated_data):
        """
        Create and return a new `Video` instance, given the validated data.
        """
        return Video.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Video` instance, given the validated data.
        """
        instance.url = validated_data.get("url", instance.url)
        instance.title = validated_data.get("title", instance.title)
        instance.save()
        return instance


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
            "created_by_id",
            "video_id",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """
        Create and return a new `Plio` instance, given the validated data.
        """
        return Plio.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Plio` instance, given the validated data.
        """
        instance.video_id = validated_data.get("video_id", instance.video_id)
        instance.name = validated_data.get("name", instance.name)
        instance.uuid = validated_data.get("uuid", instance.uuid)
        instance.failsafe_url = validated_data.get(
            "failsafe_url", instance.failsafe_url
        )
        instance.status = validated_data.get("status", instance.status)
        instance.is_public = validated_data.get("is_public", instance.is_public)
        instance.created_by_id = validated_data.get(
            "created_by_id", instance.created_by_id
        )
        instance.save()
        return instance
