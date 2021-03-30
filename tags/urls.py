from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("get_df", views.get_df),
    path("tags/", views.tag_list),
    path("tags/<int:pk>/", views.tag_detail),
]
