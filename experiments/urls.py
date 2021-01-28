from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('get_assignment', views.get_assignment),
    path('get_experiment', views._get_experiment),
    path('experiment_list', views.get_experiment_list),
]