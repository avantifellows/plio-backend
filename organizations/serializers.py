from rest_framework import serializers
from organizations.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "schema_name", "name", "shortcode", "created_at", "updated_at"]
        read_only_fields = ["schema_name"]

    def create(self, validated_data):
        """
        Create and return a new `Organization` instance, given the validated data.
        """
        return Organization.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Organization` instance, given the validated data.
        """
        instance.name = validated_data.get("name", instance.name)
        instance.shortcode = validated_data.get("shortcode", instance.shortcode)
        instance.save()
        return instance
