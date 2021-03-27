from rest_framework import serializers
from organizations.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "shortcode", "schema_name"]

    def create(self, validated_data):
        """
        Create and return a new `Organization` instance, given the validated data.
        """
        return Organization.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Organization` instance, given the validated data.
        """
        instance.title = validated_data.get("title", instance.title)
        instance.code = validated_data.get("code", instance.code)
        instance.linenos = validated_data.get("linenos", instance.linenos)
        instance.language = validated_data.get("language", instance.language)
        instance.style = validated_data.get("style", instance.style)
        instance.save()
        return instance
