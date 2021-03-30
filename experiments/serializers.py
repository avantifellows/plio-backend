from rest_framework import serializers
from experiments.models import Experiment


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = [
            "id",
            "name",
            "description",
            "is_test",
            "created_by_id",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """
        Create and return a new `Experiment` instance, given the validated data.
        """
        return Experiment.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Experiment` instance, given the validated data.
        """
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.is_test = validated_data.get("is_test", instance.is_test)
        instance.type = validated_data.get("type", instance.type)
        instance.created_by_id = validated_data.get(
            "created_by_id", instance.created_by_id
        )
        instance.save()
        return instance
