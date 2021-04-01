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
from rest_framework import routers, serializers

from tags.views import TagViewSet
from users.views import UserViewSet
from organizations.views import OrganizationViewSet
from experiments.views import ExperimentViewSet
from plio.views import VideoViewSet, PlioViewSet, ItemViewSet, QuestionViewSet
from entries.views import SessionViewSet, SessionAnswerViewSet, EventViewSet
from . import views

from django.conf.urls import url
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

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
api_router.register(r"organizations", OrganizationViewSet)
api_router.register(r"users", UserViewSet)
api_router.register(r"videos", VideoViewSet)
api_router.register(r"plios", PlioViewSet)
api_router.register(r"items", ItemViewSet)
api_router.register(r"questions", QuestionViewSet)
api_router.register(r"experiments", ExperimentViewSet)
api_router.register(r"sessions", SessionViewSet)
api_router.register(r"session-answers", SessionAnswerViewSet)
api_router.register(r"events", EventViewSet)
api_router.register(r"tags", TagViewSet)

urlpatterns = [
    path("player/", views.redirect_home),
    path("player/<str:plio_id>", views.redirect_plio),
    path("admin/", admin.site.urls),
    path("", views.index),
    path("plios_list", views.get_plios_list),
    path("get_plio", views.get_plio),
    path("create_plio", views.create_plio),
    path("get_plio_config", views._get_plio_config),
    path("get_plios_df", views.get_plios_df),
    # separate app for tags
    path("entries/", include("entries.urls")),
    # separate app for users
    path("users/", include("users.urls")),
    # separate app for experiments
    path("experiments/", include("experiments.urls")),
    # separate app for tags
    path("tags/", include("tags.urls")),
    # separate app for components
    path("components/", include("components.urls")),
    # API routes
    path("api/v1/", include(api_router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(
        r"^api/v1/docs/$",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]
