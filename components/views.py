import requests
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.http import response, HttpResponseBadRequest, request
from rest_framework.decorators import api_view
from plio.settings import DB_QUERIES_URL, FRONTEND_URL

URL_PREFIX_GET_DEFAULT_COMPONENT_CONFIG = "/get_default_component_config"
URL_PREFIX_GET_COMPONENT_FEATURES = "/get_component_features"


# Structure
# COMPONENT - for example, plio is a component. It includes our player
#             page and everything else that might be added to the page
#            Another component could be homepage, experiments page etc
# SECTION - they are sub parts of a component. Eg - currently, player
#           is a section of plio. In future, we might add text below the player
#           which will be another section of the plio
# FEATURE - These are the customizable features in a section. Eg-  progress bar
#           for the player section or color tagging for some section in the
#           experiments component
# DETAILS - These are the nitty gritty details of a feature. Eg- color of the
#           progress bar


@api_view(["GET"])
def _get_features(request):
    """
    params: type (REQUIRED) [the type of component needed]
    example: /_get_features?type=plio
    """
    component_type = request.GET.get("type", "")

    if not component_type:
        return HttpResponseNotFound("<h1>No component type specified</h1>")

    component_features = get_features(component_type)

    # if the returned object is not dict, it will be some variant
    # of HttpResponseNotFound, returning it if that's the case
    # TODO: return `JSONResponses` instead of `HttpResponse` classes wherever possible
    if not isinstance(component_features, dict):
        return component_features

    return JsonResponse(component_features, status=200)


def get_features(component_type):
    """Returns the specific component-features JSON after fetching it from S3"""

    data = requests.get(
        DB_QUERIES_URL + URL_PREFIX_GET_COMPONENT_FEATURES,
        params={"type": component_type},
    )

    if data.status_code == 404:
        return HttpResponseNotFound(f"<h1>{component_type} features not found</h1>")
    if data.status_code != 200:
        return HttpResponseNotFound("<h1>An unknown error occurred</h1>")

    return data.json()["value"]


@api_view(["GET"])
def _get_default_config(request):
    """
    params: type (REQUIRED)
    example: /get_default_component_config
    """
    component_type = request.GET.get("type", "")
    if not component_type:
        return HttpResponseNotFound("<h1>No component type specified</h1>")

    default_component_config = get_default_config(component_type)

    if not isinstance(default_component_config, dict):
        return default_component_config

    return JsonResponse(default_component_config, status=200)


def get_default_config(component_type: str):
    """Fetches the default component config from the DB"""
    default_component_config = requests.get(
        DB_QUERIES_URL + URL_PREFIX_GET_DEFAULT_COMPONENT_CONFIG,
        params={"type": component_type},
    )

    if default_component_config.status_code != 200:
        return HttpResponseNotFound("<h1>An unknown error occurred</h1>")

    return default_component_config.json()["value"]


def index(request):
    return redirect(FRONTEND_URL, permanent=True)
