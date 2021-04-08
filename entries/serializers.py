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
            "watch_time",
            "plio",
            "user",
            "created_at",
            "updated_at",
        ]

    def validate_plio(self, plio):
        """Ensure that a session is created only for a published plio"""
        if plio.status == "draft":
            raise serializers.ValidationError(
                "A session can only be created for a published plio"
            )
        return plio

    def create(self, validated_data):
        """
        Create and return a new `Session` instance, given the validated data.
        """
        # fetch all past sessions for this user-plio combination
        last_session = (
            Session.objects.filter(plio_id=validated_data["plio"].id)
            .filter(user_id=validated_data["user"].id)
            .first()
        )
        if last_session:
            last_session_data = SessionSerializer(last_session).data
            # add values for missing keys from the most recent session
            keys_to_check = [
                "retention",
                "has_video_played",
                "experiment",
                "watch_time",
            ]
            for key in keys_to_check:
                if key not in validated_data:
                    validated_data[key] = last_session_data[key]

        return Session.objects.create(**validated_data)

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["plio"] = PlioSerializer(instance.plio).data
        response["user"] = UserSerializer(instance.user).data
        if instance.experiment:
            response["experiment"] = ExperimentSerializer(instance.experiment).data
        response["last_event"] = EventSerializer(instance.last_event).data
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
