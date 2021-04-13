from rest_framework import serializers
from plio.models import Item
from plio.serializers import PlioSerializer, ItemSerializer, QuestionSerializer
from entries.models import Session, SessionAnswer, Event
from experiments.serializers import ExperimentSerializer
from users.serializers import UserSerializer
from users.models import User


class SessionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault()
    )

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

        # get the newly created session object
        session = Session.objects.create(**validated_data)

        # will store the values for creating the session answers
        session_answers = []

        # create the session answers
        if last_session:
            # copy last session answers
            keys_to_copy = ["item", "answer"]
            last_session_answers = last_session.sessionanswer_set.values(*keys_to_copy)

            for session_answer in last_session_answers:
                session_answer["session"] = session.id
                session_answers.append(session_answer)

        else:
            # create new empty session answers
            items = Item.objects.filter(plio_id=validated_data["plio"].id).values("id")
            for item in items:
                session_answers.append(
                    {
                        "item": item["id"],
                        "session": session.id,
                    }
                )

        # create the session answers
        for session_answer in session_answers:
            serializer = SessionAnswerSerializer(data=session_answer)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return session

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["plio"] = PlioSerializer(instance.plio).data
        response["user"] = UserSerializer(instance.user).data
        if instance.experiment:
            response["experiment"] = ExperimentSerializer(instance.experiment).data
        response["last_event"] = EventSerializer(instance.last_global_event).data

        # fetch and return all session answers tied to this session
        response["session_answers"] = instance.sessionanswer_set.values()
        return response


class SessionAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionAnswer
        fields = [
            "id",
            "answer",
            "item",
            "session",
            "created_at",
            "updated_at",
        ]


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
