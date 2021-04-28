from rest_framework import serializers
from tags.models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            "id",
            "name",
            "slug",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug"]

    def create(self, validated_data):
        """
        Create and return a new `Tag` instance, given the validated data.
        """
        return Tag.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Tag` instance, given the validated data.
        """
        instance.name = validated_data.get("name", instance.name)
        instance.save()
        return instance
