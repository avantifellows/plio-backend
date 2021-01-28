from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('get_config', views._get_user_config),
    path('update_config', views._update_user_config),
    path('login', views.login_user),
]