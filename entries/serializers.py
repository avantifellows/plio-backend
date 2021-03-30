from rest_framework import serializers
from entries.models import Session, SessionAnswer, Event


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = [
            "id",
            "retention",
            "has_video_played",
            "experiment_id",
            "plio_id",
            "user_id",
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
        instance.experiment_id = validated_data.get(
            "experiment_id", instance.experiment_id
        )
        instance.plio_id = validated_data.get("plio_id", instance.plio_id)
        instance.user_id = validated_data.get("user_id", instance.user_id)
        instance.save()
        return instance


class SessionAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionAnswer
        fields = [
            "id",
            "answer",
            "question_id",
            "session_id",
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
        instance.question_id = validated_data.get("question_id", instance.question_id)
        instance.session_id = validated_data.get("session_id", instance.session_id)
        instance.save()
        return instance


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "session_id",
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
        instance.session_id = validated_data.get("session_id", instance.session_id)
        instance.type = validated_data.get("type", instance.type)
        instance.player_time = validated_data.get("player_time", instance.player_time)
        instance.details = validated_data.get("details", instance.details)
        instance.save()
        return instance
