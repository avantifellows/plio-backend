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
from rest_framework import routers, serializers, viewsets
from users.models import User
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from users.models import User
from users.serializers import UserSerializer
from . import views

# ViewSets define the view behavior.
class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


api_router = routers.DefaultRouter()
api_router.register(r"organizations", OrganizationViewSet)
api_router.register(r"users", UserViewSet)

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
    path("api/v1/", include(api_router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
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
]
