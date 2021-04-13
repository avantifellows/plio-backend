from django.urls import path
from . import views

urlpatterns = [
    path("get_config", views._get_user_config),
    path("update_config", views._update_user_config),
]
