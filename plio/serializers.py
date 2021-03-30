from rest_framework import serializers
from plio.models import Video, Plio, Item, Question


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
            "created_by",
            "video",
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
        instance.video = validated_data.get("video", instance.video)
        instance.name = validated_data.get("name", instance.name)
        instance.uuid = validated_data.get("uuid", instance.uuid)
        instance.failsafe_url = validated_data.get(
            "failsafe_url", instance.failsafe_url
        )
        instance.status = validated_data.get("status", instance.status)
        instance.is_public = validated_data.get("is_public", instance.is_public)
        instance.created_by = validated_data.get("created_by", instance.created_by)
        instance.save()
        return instance


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            "plio",
            "type",
            "text",
            "time",
            "meta",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """
        Create and return a new `Item` instance, given the validated data.
        """
        return Item.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Item` instance, given the validated data.
        """
        instance.plio = validated_data.get("plio", instance.plio)
        instance.type = validated_data.get("type", instance.type)
        instance.text = validated_data.get("text", instance.text)
        instance.time = validated_data.get("time", instance.time)
        instance.meta = validated_data.get("meta", instance.meta)
        instance.save()
        return instance


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "item",
            "type",
            "options",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """
        Create and return a new `Question` instance, given the validated data.
        """
        return Question.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Question` instance, given the validated data.
        """
        instance.item = validated_data.get("item", instance.item)
        instance.type = validated_data.get("type", instance.type)
        instance.options = validated_data.get("options", instance.options)
        instance.save()
        return instance
