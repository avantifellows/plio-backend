from rest_framework import serializers
from tags.models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            "name",
            "slug",
            "created_at",
            "updated_at",
        ]

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
        instance.slug = validated_data.get("slug", instance.slug)
        instance.save()
        return instance
