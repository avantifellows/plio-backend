from rest_framework import serializers
from users.models import User


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
