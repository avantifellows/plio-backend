from django.urls import path
from . import views

urlpatterns = [
    path("get_assignment", views.get_assignment),
]
