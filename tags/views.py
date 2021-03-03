import requests
import json
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from rest_framework.decorators import api_view

from plio.settings import DB_QUERIES_URL
from utils.data import convert_objects_to_df

URL_PREFIX_GET_ALL_TAGS = '/get_tags'	


def index(request):
    return redirect('https://player.plio.in', permanent=True)


@api_view(['GET'])
def get_df(request):
    """Returns a dataframe for all tags"""	
    tags = fetch_all_tags()

    # if the returned object is not dict, it will be some variant
    # of HttpResponseNotFound, returning it if that's the case
    if not isinstance(tags, list):
        return tags

    tags_df = convert_objects_to_df(tags)

    return JsonResponse(tags_df.to_dict())



def fetch_all_tags():
    response = requests.get(DB_QUERIES_URL + URL_PREFIX_GET_ALL_TAGS)
    if (response.status_code != 200):	
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    return json.loads(response.json())