from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('get_default_config', views._get_default_component_config),
    path('get_features', views._get_component_features),
]