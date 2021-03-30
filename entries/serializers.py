from rest_framework import serializers
from entries.models import Session, SessionAnswer, Event


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = [
            "id",
            "retention",
            "has_video_played",
            "experiment",
            "plio",
            "user",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """
        Create and return a new `Session` instance, given the validated data.
        """
        return Session.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Session` instance, given the validated data.
        """
        instance.retention = validated_data.get("retention", instance.retention)
        instance.has_video_played = validated_data.get(
            "has_video_played", instance.has_video_played
        )
        instance.experiment = validated_data.get("experiment", instance.experiment)
        instance.plio = validated_data.get("plio", instance.plio)
        instance.user = validated_data.get("user", instance.user)
        instance.save()
        return instance


class SessionAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionAnswer
        fields = [
            "id",
            "answer",
            "question",
            "session",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """
        Create and return a new `SessionAnswer` instance, given the validated data.
        """
        return SessionAnswer.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `SessionAnswer` instance, given the validated data.
        """
        instance.answer = validated_data.get("answer", instance.answer)
        instance.question = validated_data.get("question", instance.question)
        instance.session = validated_data.get("session", instance.session)
        instance.save()
        return instance


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "session",
            "type",
            "player_time",
            "details",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """
        Create and return a new `Event` instance, given the validated data.
        """
        return Event.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Event` instance, given the validated data.
        """
        instance.session = validated_data.get("session", instance.session)
        instance.type = validated_data.get("type", instance.type)
        instance.player_time = validated_data.get("player_time", instance.player_time)
        instance.details = validated_data.get("details", instance.details)
        instance.save()
        return instance
