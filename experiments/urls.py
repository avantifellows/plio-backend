from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("get_assignment", views.get_assignment),
    path("get_df", views.get_df),
    path("experiments/", views.experiment_list),
    path("experiments/<int:pk>/", views.experiment_detail),
]
