from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("get_df", views.get_df),
    path("update", views.update_entry),
    path("sessions/", views.session_list),
    path("sessions/<int:pk>/", views.session_detail),
    path("session-answers/", views.session_answer_list),
    path("session-answers/<int:pk>/", views.session_answer_detail),
    path("events/", views.event_list),
    path("events/<int:pk>/", views.event_detail),
]
