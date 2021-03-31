from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("get_df", views.get_df),
    path("update", views.update_entry),
]
