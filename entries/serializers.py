from rest_framework import serializers
from entries.models import Session, SessionAnswer, Event
from plio.serializers import PlioSerializer
from experiments.serializers import ExperimentSerializer
from users.serializers import UserSerializer
from plio.serializers import QuestionSerializer


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

    def validate_plio(self, value):
        """Ensure that a session is created only for a published plio"""
        if value.status == "draft":
            raise serializers.ValidationError(
                "A session can only be created for a published plio"
            )
        return value

    def create(self, validated_data):
        """
        Create and return a new `Session` instance, given the validated data.
        """
        return Session.objects.create(**validated_data)

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["plio"] = PlioSerializer(instance.plio).data
        response["user"] = UserSerializer(instance.user).data
        if instance.experiment:
            response["experiment"] = ExperimentSerializer(instance.experiment).data
        return response


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

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["question"] = QuestionSerializer(instance.question).data
        response["session"] = SessionSerializer(instance.session).data
        return response


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "type",
            "player_time",
            "details",
            "session",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["session"] = SessionSerializer(instance.session).data
        return response
