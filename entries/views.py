import requests
import json
import logging
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.http import response, HttpResponseBadRequest, request
from rest_framework.decorators import api_view
from rest_framework.request import Request
import pandas as pd
from datetime import datetime

from plio.settings import DB_QUERIES_URL, FRONTEND_URL
from utils.data import convert_objects_to_df
from utils.security import hash_function
from utils.cleanup import is_valid_user_id
from utils.request import get_user_agent_info

from rest_framework import viewsets
from entries.models import Session, SessionAnswer, Event
from entries.serializers import (
    SessionSerializer,
    SessionAnswerSerializer,
    EventSerializer,
)

URL_PREFIX_GET_ALL_ENTRIES = "/get_entries"
URL_PREFIX_UPDATE_ENTRY = "/update_response_entry"


def index(request):
    return redirect(FRONTEND_URL, permanent=True)


@api_view(["GET"])
def get_df(request):
    """Returns a dataframe for all entries"""
    logging.info("Fetching all entries df")
    entries = fetch_all_entries()

    # if the returned object is not dict, it will be some variant
    # of HttpResponseNotFound, returning it if that's the case
    if not isinstance(entries, list):
        return entries

    entries_df = convert_objects_to_df(entries)
    preprocess = json.loads(request.GET.get("preprocess", "True").lower())

    if preprocess:
        # add secret key to each entry
        entries_df["secret_key"] = entries_df["user-id"].apply(hash_function)

        # handle country code if not already present
        entries_df["user-id"] = entries_df["user-id"].apply(
            lambda _id: _id if len(_id) > 10 else f"91{_id}"
        )

        # remove test entries
        entries_df = remove_entries_from_test_users(entries_df, "user-id")

        # convert msec to sec
        entries_df["watch-time"] /= 1000

    return JsonResponse(entries_df.to_dict())


def fetch_all_entries():
    print("Fetching")
    response = requests.get(DB_QUERIES_URL + URL_PREFIX_GET_ALL_ENTRIES)
    if response.status_code != 200:
        return HttpResponseNotFound("<h1>An unknown error occurred</h1>")

    print("Done")
    return json.loads(response.json())


def remove_entries_from_test_users(
    entries_df: pd.DataFrame, entry_user_id_key: str
) -> pd.DataFrame:
    """Removes test user IDs from the entries dataframe"""
    return entries_df[
        entries_df[entry_user_id_key].apply(is_valid_user_id)
    ].reset_index(drop=True)


@api_view(["POST"])
def update_entry(request: Request):
    """Push plio response JSON to s3

    request.data = {
        'response': {
            'answers' : list of integers,
            'watch-time' : integer,
            'user-id' : string,
            'plio-id' : string,
            'session-id' : integer,
            'source' : string,
            'retention' : list of integers,
            'has-video-played' : integer,
            'journey' : list of dicts
        }
    }
    """
    request.data["response"]["user_agent"] = get_user_agent_info(request)

    # add creation date
    request.data["response"]["creation_date"] = f"{datetime.now():%Y-%m-%d %H:%M:%S}"

    params = {"response": request.data["response"]}

    result = requests.post(DB_QUERIES_URL + URL_PREFIX_UPDATE_ENTRY, json=params)

    return JsonResponse({"result": result.json()}, status=result.status_code)


class SessionViewSet(viewsets.ModelViewSet):
    """
    Session ViewSet description

    list: List all sessions
    retrieve: Retrieve a session
    update: Update a session
    create: Create a session
    partial_update: Patch a session
    destroy: Soft delete a session
    """

    serializer_class = SessionSerializer

    def get_queryset(self):
        queryset = Session.objects.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SessionAnswerViewSet(viewsets.ModelViewSet):
    """
    SessionAnswer ViewSet description

    list: List all session answers
    retrieve: Retrieve a session answer
    update: Update a session answer
    create: Create a session answer
    partial_update: Patch a session answer
    destroy: Soft delete a session answer
    """

    queryset = SessionAnswer.objects.all()
    serializer_class = SessionAnswerSerializer


class EventViewSet(viewsets.ModelViewSet):
    """
    Event ViewSet description

    list: List all events
    retrieve: Retrieve a event
    update: Update a event
    create: Create a event
    partial_update: Patch a event
    destroy: Soft delete a event
    """

    queryset = Event.objects.all()
    serializer_class = EventSerializer
