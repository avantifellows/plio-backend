from rest_framework import serializers
from organizations.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "schema_name",
            "name",
            "shortcode",
            "api_key",
            "config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["schema_name"]
