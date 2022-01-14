from rest_framework import serializers
from users.models import User, OneTimePassword, Role, OrganizationUser
from organizations.serializers import OrganizationSerializer
from django.core.cache import cache
from plio.cache import get_cache_key


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
        # check if a cached version exists and if it does, return it as the response
        cache_key = get_cache_key(instance)
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response

        response = super().to_representation(instance)
        # add organizations the user is a part of to the response
        response["organizations"] = OrganizationSerializer(
            instance.organizations, many=True
        ).data
        # for each organization the user is part of, add the user's role in
        # that organization
        for org in response["organizations"]:
            org_user_instance = OrganizationUser.objects.filter(
                user=instance, organization_id=org["id"]
            ).first()
            role_id = OrganizationUserSerializer(org_user_instance).data["role"]
            role_name = RoleSerializer(Role.objects.filter(id=role_id).first()).data[
                "name"
            ]
            org.update({"role": role_name})

        cache.set(cache_key, response)  # set a cached version
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
