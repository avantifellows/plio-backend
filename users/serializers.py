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
            "phone",
            "avatar_url",
            "config",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"password": {"write_only": True}}


class OtpSerializer(serializers.ModelSerializer):
    # mobile = serializers.CharField(max_length=20)
    # otp = serializers.CharField(max_length=10)
    # expires_at = serializers.DateTimeField()
    # created_at = serializers.DateTimeField()
    # updated_at = serializers.DateTimeField()

    class Meta:
        model = OneTimePassword
        fields = [
            "id",
            "mobile",
            "expires_at",
            "created_at",
            "updated_at",
        ]
