from rest_framework import serializers
from experiments.models import Experiment
from users.serializers import UserSerializer


class ExperimentSerializer(serializers.ModelSerializer):
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
