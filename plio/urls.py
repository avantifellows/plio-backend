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
from plio.models import Video, Plio, Item, Question
from plio.serializers import (
    VideoSerializer,
    PlioSerializer,
    ItemSerializer,
    QuestionSerializer,
)
from experiments.models import Experiment
from experiments.serializers import ExperimentSerializer
from tags.models import Tag
from tags.serializers import TagSerializer
from entries.models import Session, SessionAnswer, Event
from entries.serializers import (
    SessionSerializer,
    SessionAnswerSerializer,
    EventSerializer,
)
from . import views


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer


class PlioViewSet(viewsets.ModelViewSet):
    queryset = Plio.objects.all()
    serializer_class = PlioSerializer


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


class ExperimentViewSet(viewsets.ModelViewSet):
    queryset = Experiment.objects.all()
    serializer_class = ExperimentSerializer


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer


class SessionAnswerViewSet(viewsets.ModelViewSet):
    queryset = SessionAnswer.objects.all()
    serializer_class = SessionAnswerSerializer


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


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
    path("videos/", views.video_list),
    path("videos/<int:pk>/", views.video_detail),
    path("plios/", views.plio_list),
    path("plios/<int:pk>/", views.plio_detail),
    path("items/", views.item_list),
    path("items/<int:pk>/", views.item_detail),
    path("questions/", views.question_list),
    path("questions/<int:pk>/", views.question_detail),
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
