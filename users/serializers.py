from rest_framework import serializers
from users.models import User, OneTimePassword, Role, OrganizationUser
from organizations.serializers import OrganizationSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "last_login",
            "password",
            "is_superuser",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "date_joined",
            "email",
            "mobile",
            "avatar_url",
            "config",
            "created_at",
            "updated_at",
            "organizations",
            "status",
            "unique_id",
            "auth_org",
        ]
        extra_kwargs = {"password": {"write_only": True}}
        read_only_fields = ["is_superuser", "is_staff"]

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["organizations"] = OrganizationSerializer(
            instance.organizations, many=True
        ).data
        return response

    def validate_config(self, config):
        """Validates the config value for the user"""
        if not isinstance(config, dict):
            raise serializers.ValidationError("Config should be a dictionary")
        return config


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "created_at",
            "updated_at",
        ]


class OtpSerializer(serializers.ModelSerializer):
    class Meta:
        model = OneTimePassword
        fields = [
            "id",
            "mobile",
            "expires_at",
            "created_at",
            "updated_at",
        ]


class OrganizationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationUser
        fields = [
            "user",
            "organization",
            "is_owner",
            "role",
        ]
