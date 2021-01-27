from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('get_assignment', views.get_assignment)
]