import datetime
import string
import random
import requests

from django.utils import timezone
from django.contrib.auth import login

from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from oauth2_provider.models import AccessToken, Application, RefreshToken

from plio.settings import (
    API_APPLICATION_NAME,
    OAUTH2_PROVIDER,
    OTP_EXPIRE_SECONDS,
    ANALYTICS_IDP,
    SMS_DRIVER,
)
from users.models import User, OneTimePassword, OrganizationUser
from users.serializers import UserSerializer, OtpSerializer, OrganizationUserSerializer
from users.permissions import UserPermission, OrganizationUserPermission
from organizations.models import Organization
from .services import SnsService
from .config import required_third_party_auth_keys


class UserViewSet(viewsets.ModelViewSet):
    """
    User ViewSet description

    list: List all users
    retrieve: Retrieve a user
    update: Update a user
    create: Create a user
    partial_update: Patch a user
    destroy: Soft delete a user
    config: Retrieve or update user config
    """

    permission_classes = [IsAuthenticated, UserPermission]
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(
        detail=True,
        permission_classes=[IsAuthenticated, UserPermission],
        methods=["put"],
    )
    def setting(self, request, pk):
        """Updates a user's setting key inside it's config"""
        user = self.get_object()
        if "settings" not in user.config:
            user.config["settings"] = {}

        user.config["settings"] = self.request.data
        user.save()
        return Response(
            self.get_serializer(user).data["config"], status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["patch", "get"],
        permission_classes=[IsAuthenticated, UserPermission],
    )
    def config(self, request, pk):
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

    permission_classes = [IsAuthenticated, OrganizationUserPermission]
    queryset = OrganizationUser.objects.all()
    serializer_class = OrganizationUserSerializer

    def get_queryset(self):
        # get all organizations where the current user is a super-admin or org-admin
        if not self.request.user:
            return OrganizationUser.objects.none()

        if self.request.user.is_superuser:
            return OrganizationUser.objects.all()

        user_organizations = OrganizationUser.objects.filter(
            user=self.request.user, role__name__in=["super-admin", "org-admin"]
        ).all()

        # get the array of organization ids
        organization_ids = [
            user_organization.organization_id
            for user_organization in user_organizations
        ]

        # return instances that falls under the organization ids
        return OrganizationUser.objects.filter(organization__in=organization_ids)


def login_user_and_get_access_token(user, request):
    # define the backend authenticator
    user.backend = "oauth2_provider.contrib.rest_framework.OAuth2Authentication"
    login(request, user)

    # define an application
    application = Application.objects.get(name=API_APPLICATION_NAME)
    # get the newly generated access/refresh tokens for the user and application
    return get_new_access_token(user, application)


def get_new_access_token(user, application):
    """Creates a new access + refresh token for the given user and application"""
    expire_seconds = OAUTH2_PROVIDER["ACCESS_TOKEN_EXPIRE_SECONDS"]
    scopes = " ".join(OAUTH2_PROVIDER["DEFAULT_SCOPES"])
    expires = timezone.now() + datetime.timedelta(seconds=expire_seconds)
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

    return {
        "access_token": access_token.token,
        "token_type": "Bearer",
        "expires_in": expire_seconds,
        "refresh_token": refresh_token.token,
        "scope": scopes,
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def request_otp(request):
    otp = OneTimePassword()
    otp.mobile = request.data["mobile"]
    otp.otp = random.randint(100000, 999999)
    otp.expires_at = timezone.now() + datetime.timedelta(seconds=OTP_EXPIRE_SECONDS)
    otp.save()

    if SMS_DRIVER == "sns":
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
            mobile=mobile, otp=otp, expires_at__gte=timezone.now()
        ).first()
        if not otp:
            raise OneTimePassword.DoesNotExist
        otp.delete()

        # find or create the user that has the same mobile number
        user = User.objects.filter(mobile=mobile).first()
        if not user:
            user = User.objects.create_user(mobile=mobile)

        # login the user, get the new access token and return
        token = login_user_and_get_access_token(user, request)
        return Response(token, status=status.HTTP_200_OK)

    except OneTimePassword.DoesNotExist:
        return Response({"detail": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["GET"])
def get_by_access_token(request):
    if "token" not in request.query_params:
        return Response(
            {"detail": "token not provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token = request.query_params["token"]
    access_token = AccessToken.objects.filter(token=token).first()
    if access_token:
        user = User.objects.filter(id=access_token.user_id).first()
        return Response(UserSerializer(user).data)

    return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@permission_classes([AllowAny])
def generate_external_auth_access_token(request):
    """
    Generate an access token for the given combination of unique user id and an org's API_KEY
    """
    # all the required auth keys should be present in the request
    for key in required_third_party_auth_keys:
        if key not in request.data:
            return Response(
                {"detail": f"{key} not provided."}, status=status.HTTP_400_BAD_REQUEST
            )

    # check if the api_key is valid and exists
    api_key = Organization.objects.filter(api_key=request.data["api_key"])
    if not api_key.exists():
        return Response(
            {"detail": "Invalid api_key provided."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # the org to which this api_key belongs to
    requesting_org = api_key.first()

    # check if the requested user exists or not
    user = User.objects.filter(
        unique_id=request.data["unique_id"], auth_org=requesting_org
    ).first()

    # create a new user and link it to the org
    # if it doesn't already exist
    if not user:
        user = User.objects.create_user(
            unique_id=request.data["unique_id"], auth_org=requesting_org
        )

    # login the user, get the new access token and return
    token = login_user_and_get_access_token(user, request)
    return Response(token, status=status.HTTP_200_OK)


@api_view(["POST"])
def retrieve_analytics_app_access_token(request):
    """Requests the configured identity provider to retrieve an access token."""

    payload = {
        "grant_type": "client_credentials",
        "client_id": ANALYTICS_IDP["client_id"],
        "client_secret": ANALYTICS_IDP["client_secret"],
    }
    if ANALYTICS_IDP["type"] == "auth0":
        payload["audience"] = ANALYTICS_IDP["audience"]

    response = requests.post(ANALYTICS_IDP["token_url"], data=payload)
    return Response(response.json(), status=status.HTTP_200_OK)
