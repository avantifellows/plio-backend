from rest_framework import serializers
from users.models import User, OneTimePassword, Role
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
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response["organizations"] = OrganizationSerializer(
            instance.organizations, many=True
        ).data
        return response


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
