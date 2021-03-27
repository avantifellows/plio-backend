from django.urls import path
from organizations import views

urlpatterns = [
    path("organizations/", views.organization_list),
    path("organizations/<int:pk>/", views.organization_detail),
]
