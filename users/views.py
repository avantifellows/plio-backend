from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny

from plio.settings import (
    API_APPLICATION_NAME,
    OAUTH2_PROVIDER,
    OTP_EXPIRE_SECONDS,
    AUTH0_TOKEN_URL,
    AUTH0_CLIENT_ID,
    AUTH0_CLIENT_SECRET,
    AUTH0_AUDIENCE,
)

from rest_framework import viewsets, status
from rest_framework.response import Response
from users.models import User, OneTimePassword, OrganizationUser
from users.serializers import UserSerializer, OtpSerializer, OrganizationUserSerializer

import datetime
import string
import random
from django.contrib.auth import login
from oauth2_provider.models import AccessToken, Application, RefreshToken
from .services import SnsService

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save, post_delete

import requests


class UserViewSet(viewsets.ModelViewSet):
    """
    User ViewSet description

    list: List all users
    retrieve: Retrieve a user
    update: Update a user
    create: Create a user
    partial_update: Patch a user
    destroy: Soft delete a user
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=True, methods=["patch", "get"])
    def config(self, request, pk=True):
        user = self.get_object()
        if request.method == "GET":
            return Response(user.config)

        if request.method == "PATCH":
            # config is not passed
            if "config" not in request.data:
                return Response(
                    {"detail": "config not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # other keys apart from config are also passed
            if len(request.data.keys()) > 1:
                return Response(
                    {"detail": "extra keys apart from config are not allowed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = UserSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"status": "config set"})


class OrganizationUserViewSet(viewsets.ModelViewSet):
    """
    OrganizationUser ViewSet description

    list: List all organization users
    retrieve: Retrieve an organization user
    update: Update an organization user
    create: Create an organization user
    partial_update: Patch an organization user
    destroy: Soft delete an organization user
    """

    queryset = OrganizationUser.objects.all()
    serializer_class = OrganizationUserSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def request_otp(request):
    otp = OneTimePassword()
    otp.mobile = request.data["mobile"]
    otp.otp = random.randint(100000, 999999)
    otp.expires_at = datetime.datetime.now() + datetime.timedelta(
        seconds=OTP_EXPIRE_SECONDS
    )
    otp.save()

    sms = SnsService()
    sms.publish(
        otp.mobile,
        f"Hello! Your OTP for Plio login is {otp.otp}. It is valid for the next 5 minutes. Please do not share it with anyone.",
    )

    return Response(OtpSerializer(otp).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    mobile = request.data["mobile"]
    otp = request.data["otp"]
    try:
        otp = OneTimePassword.objects.filter(
            mobile=mobile, otp=otp, expires_at__gte=datetime.datetime.now()
        ).first()
        if not otp:
            raise OneTimePassword.DoesNotExist
        otp.delete()

        # find or create the user that has the same mobile number
        user = User.objects.filter(mobile=mobile).first()
        if not user:
            user = User.objects.create_user(mobile=mobile)

        # define the backend authenticator
        user.backend = "oauth2_provider.contrib.rest_framework.OAuth2Authentication"
        login(request, user)

        expire_seconds = OAUTH2_PROVIDER["ACCESS_TOKEN_EXPIRE_SECONDS"]
        scopes = " ".join(OAUTH2_PROVIDER["DEFAULT_SCOPES"])

        application = Application.objects.get(name=API_APPLICATION_NAME)
        expires = datetime.datetime.now() + datetime.timedelta(seconds=expire_seconds)
        random_token = "".join(random.choices(string.ascii_lowercase, k=30))
        # generate oauth2 access token
        access_token = AccessToken.objects.create(
            user=user,
            application=application,
            token=random_token,
            expires=expires,
            scope=scopes,
        )

        random_token = "".join(random.choices(string.ascii_lowercase, k=30))
        # generate oauth2 refresh token
        refresh_token = RefreshToken.objects.create(
            user=user,
            token=random_token,
            access_token=access_token,
            application=application,
        )

        token = {
            "access_token": access_token.token,
            "token_type": "Bearer",
            "expires_in": expire_seconds,
            "refresh_token": refresh_token.token,
            "scope": scopes,
        }

        return Response(token, status=status.HTTP_200_OK)

    except OneTimePassword.DoesNotExist:
        return Response({"detail": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["GET"])
def get_by_access_token(request):
    token = request.query_params["token"]
    access_token = AccessToken.objects.filter(token=token).first()
    if access_token:
        user = User.objects.filter(id=access_token.user_id).first()
        return Response(UserSerializer(user).data)

    return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)


@receiver(pre_save, sender=User)
def update_user(sender, instance: User, **kwargs):
    if not instance.id:
        # new user is created
        return

    # existing user is updated
    old_instance = sender.objects.get(id=instance.id)
    if old_instance.status != instance.status:
        # execute this only if the user status has changed
        user_data = UserSerializer(instance).data
        channel_layer = get_channel_layer()
        user_group_name = f"user_{user_data['id']}"
        async_to_sync(channel_layer.group_send)(
            user_group_name, {"type": "send_user", "data": user_data}
        )


@receiver(post_save, sender=OrganizationUser)
@receiver(post_delete, sender=OrganizationUser)
def update_organization_user(sender, instance: OrganizationUser, **kwargs):
    # execute this if a user is added to/removed from an organization
    user_data = UserSerializer(instance.user).data
    channel_layer = get_channel_layer()
    user_group_name = f"user_{user_data['id']}"
    async_to_sync(channel_layer.group_send)(
        user_group_name, {"type": "send_user", "data": user_data}
    )


@api_view(["POST"])
def retrieve_analytics_app_access_token(request):
    """ Makes a client credentials request to Auth0 app to get an access token. """
    url = AUTH0_TOKEN_URL
    payload = {
        "grant_type": "client_credentials",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "audience": AUTH0_AUDIENCE,
    }
    response = requests.post(url, data=payload)
    return Response(response.json(), status=status.HTTP_200_OK)
