from rest_framework import serializers
from experiments.models import Experiment, ExperimentPlio
from users.serializers import UserSerializer
from plio.serializers import PlioSerializer
from users.models import User


class ExperimentSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Experiment
        fields = [
            "id",
            "name",
            "description",
            "is_test",
            "type",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["created_by"] = UserSerializer(instance.created_by).data
        return response


class ExperimentPlioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperimentPlio
        fields = ["id", "experiment", "plio", "split_percentage"]

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["experiment"] = ExperimentSerializer(instance.experiment).data
        response["plio"] = PlioSerializer(instance.plio).data
        return response
