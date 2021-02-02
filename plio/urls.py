"""plio URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('player/', views.redirect_home),
    path('player/<str:plio_id>', views.redirect_plio),
    path('admin/', admin.site.urls),
    path('', views.index),
    path('plios_list', views.get_plios_list),
    path('get_plio', views.get_plio),
    path('update_response', views.update_response),
    path('get_default_component_config', views._get_default_component_config),
    path('get_plio_config', views._get_plio_config),
    path('get_component_features', views._get_component_features),

    # separate app for users
    path('users/', include('users.urls')),

    # separate app for experiments
    path('experiments/', include('experiments.urls')),
]