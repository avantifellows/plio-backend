from rest_framework import serializers
from users.models import User, OneTimePassword


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
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_config(self, config):
        """Validates the config value for the user"""
        if not isinstance(config, dict):
            raise serializers.ValidationError("Config should be a dictionary")
        return config


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
