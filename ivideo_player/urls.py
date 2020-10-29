from django.urls import path
import boto3

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    # ex: /watcher/Xyz123
    path('<str:ivideo_id>', views.watch_ivideo, name='watch_ivideo'),
    path('<str:ivideo_id>/watch', views.watch_ivideo, name='watch_ivideo'),
    path('<str:ivideo_id>/edit', views.edit_ivideo, name='watch_ivideo')
]