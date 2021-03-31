import requests
import json
import logging
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from rest_framework.decorators import api_view

from plio.settings import DB_QUERIES_URL, FRONTEND_URL
from utils.data import convert_objects_to_df

from rest_framework import viewsets
from tags.models import Tag
from tags.serializers import TagSerializer

URL_PREFIX_GET_ALL_TAGS = "/get_tags"


def index(request):
    return redirect(FRONTEND_URL, permanent=True)


@api_view(["GET"])
def get_df(request):
    """Returns a dataframe for all tags"""
    logging.info("Fetching all tags df")
    tags = fetch_all_tags()

    # if the returned object is not dict, it will be some variant
    # of HttpResponseNotFound, returning it if that's the case
    if not isinstance(tags, list):
        return tags

    tags_df = convert_objects_to_df(tags)

    return JsonResponse(tags_df.to_dict())


def fetch_all_tags():
    response = requests.get(DB_QUERIES_URL + URL_PREFIX_GET_ALL_TAGS)
    if response.status_code != 200:
        return HttpResponseNotFound("<h1>An unknown error occurred</h1>")

    return json.loads(response.json())


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
