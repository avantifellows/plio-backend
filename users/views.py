import requests
import json
import math
import logging
import pandas as pd
from django.shortcuts import redirect
from django.http import HttpResponseNotFound, JsonResponse
from rest_framework.decorators import api_view, action
from plio.settings import (
    DB_QUERIES_URL,
    FRONTEND_URL,
    API_APPLICATION_NAME,
    OAUTH2_PROVIDER,
    OTP_EXPIRE_SECONDS,
)

from utils.s3 import create_user_profile
from utils.data import convert_objects_to_df
from utils.cleanup import is_valid_user_id
from utils.security import hash_function

from rest_framework import viewsets, response, status
from users.models import User, OneTimePassword
from users.serializers import UserSerializer, OtpSerializer

import datetime
import string
import random
from django.contrib.auth import login
from oauth2_provider.models import AccessToken, Application, RefreshToken
from .services import SnsService

URL_PREFIX_GET_USER_CONFIG = "/get_user_config"
URL_PREFIX_UPDATE_USER_CONFIG = "/update_user_config"


def get_user_config(user_id):
    """Returns the user config for the given user ID"""
    if not user_id:
        return HttpResponseNotFound("<h1>No user ID specified</h1>")

    data = requests.get(
        DB_QUERIES_URL + URL_PREFIX_GET_USER_CONFIG,
        params={"user_id": get_valid_user_id(user_id)},
    )

    if data.status_code == 404:
        return HttpResponseNotFound("<h1>No config found for this user ID</h1>")
    if data.status_code != 200:
        return HttpResponseNotFound("<h1>An unknown error occurred</h1>")

    return data.json()["user_config"]


@api_view(["GET"])
def _get_user_config(request):
    user_id = request.GET.get("user-id", "")
    config = get_user_config(user_id)
    if not isinstance(config, dict):
        return config

    return JsonResponse(config, status=200)


def update_user_config(user_id, config_data):
    """Function to update user config given user Id and config"""
    params = {"user_id": get_valid_user_id(user_id), "configs": config_data}

    requests.post(DB_QUERIES_URL + URL_PREFIX_UPDATE_USER_CONFIG, json=params)
    return JsonResponse({"status": "Success! Config updated"}, status=200)


@api_view(["POST"])
def _update_user_config(request):
    """Update the user config"""
    user_id = request.data.get("user-id", "")
    config_data = request.data.get("configs", "")

    if not user_id:
        return HttpResponseNotFound("<h1>No user-id specified</h1>")
    if not config_data:
        return HttpResponseNotFound("<h1>No tutorial data specified</h1>")

    return update_user_config(user_id, config_data)


def get_valid_user_id(user_id: str, country_code: int = 91) -> str:
    """Returns the country-code prefixed user ID

    :param user_id: user Id to be checked/edited
    :type user_id: str
    :param user_id: country code to be used; defaults to 91 (India)
    :type user_id: str
    """
    if len(user_id) == 12:
        return user_id

    return f"{country_code}{user_id}"


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
            return response.Response(user.config)

        if request.method == "PATCH":
            # config is not passed
            if "config" not in request.data:
                return response.Response(
                    {"detail": "config not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # other keys apart from config are also passed
            if len(request.data.keys()) > 1:
                return response.Response(
                    {"detail": "extra keys apart from config are not allowed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = UserSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return response.Response({"status": "config set"})


@api_view(["POST"])
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
        f"Hello! Your OTP for Plio login is {otp.otp}. Please do not share it with anyone.",
    )

    return response.Response(OtpSerializer(otp).data)


@api_view(["POST"])
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

        return response.Response(token, status=status.HTTP_200_OK)

    except OneTimePassword.DoesNotExist:
        return response.Response(
            {"detail": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(["GET"])
def get_by_access_token(request):
    token = request.query_params["token"]
    access_token = AccessToken.objects.filter(token=token).first()
    if access_token:
        user = User.objects.filter(id=access_token.user_id).first()
        return response.Response(UserSerializer(user).data)

    return response.Response(
        {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
    )
