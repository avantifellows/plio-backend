"""plio URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import url
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from tags.views import TagViewSet
from users.views import (
    UserViewSet,
    OrganizationUserViewSet,
    request_otp,
    verify_otp,
    get_by_access_token,
    generate_external_auth_access_token,
)
from organizations.views import OrganizationViewSet
from experiments.views import ExperimentViewSet, ExperimentPlioViewSet
from plio.views import (
    VideoViewSet,
    PlioViewSet,
    ItemViewSet,
    QuestionViewSet,
    ImageViewSet,
)
from entries.views import SessionViewSet, SessionAnswerViewSet, EventViewSet
from users import consumers
from etl.views import BigqueryJobsViewSet

schema_view = get_schema_view(
    openapi.Info(
        title="Plio API",
        default_version="v1",
        description="Welcome to Plio's REST API documentation!",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="admin@plio.in"),
        license=openapi.License(
            name="MIT License",
            url="https://github.com/avantifellows/plio-backend/blob/master/LICENSE",
        ),
        link="https://github.com/avantifellows/plio-backend",
    ),
    url="https://plio.in",
    public=True,
    permission_classes=[permissions.AllowAny],
)

api_router = routers.DefaultRouter()
api_router.register(r"organizations", OrganizationViewSet, basename="organizations")
api_router.register(r"users", UserViewSet, basename="users")
api_router.register(r"videos", VideoViewSet, basename="videos")
# https://stackoverflow.com/questions/48548622/base-name-argument-not-specified-and-could-not-automatically-determine-the-name
api_router.register(r"plios", PlioViewSet, basename="plios")
api_router.register(r"items", ItemViewSet, basename="items")
api_router.register(r"questions", QuestionViewSet, basename="questions")
api_router.register(r"experiments", ExperimentViewSet, basename="experiments")
api_router.register(
    r"experiment-plios", ExperimentPlioViewSet, basename="experiment-plios"
)
api_router.register(r"sessions", SessionViewSet, basename="sessions")
api_router.register(
    r"session-answers", SessionAnswerViewSet, basename="session-answers"
)
api_router.register(r"events", EventViewSet, basename="events")
api_router.register(r"tags", TagViewSet, basename="tags")
api_router.register(
    r"organization-users", OrganizationUserViewSet, basename="organization-users"
)
api_router.register(r"images", ImageViewSet, basename="images")
api_router.register(r"bigquery-jobs", BigqueryJobsViewSet, basename="bigquery-jobs")

# http/https url patterns
urlpatterns = [
    path("admin/", admin.site.urls),
    # API routes
    path("api/v1/otp/request/", request_otp, name="request-otp"),
    path("api/v1/otp/verify/", verify_otp, name="verify-otp"),
    path("api/v1/users/token/", get_by_access_token, name="get-by-access-token"),
    path(
        "auth/generate-external-auth-access-token/",
        generate_external_auth_access_token,
        name="generate_external_auth_access_token",
    ),
    path("api/v1/", include(api_router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"^auth/", include("rest_framework_social_oauth2.urls")),
    url(
        r"^api/v1/docs/$",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]

urlpatterns += [url(r"^silk/", include("silk.urls", namespace="silk"))]

# ws/wss url patterns
websocket_urlpatterns = [
    # consumer for a particular user
    path("api/v1/users/<int:user_id>", consumers.UserConsumer.as_asgi()),
]
