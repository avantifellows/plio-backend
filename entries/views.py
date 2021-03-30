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

from django.views.decorators.csrf import csrf_exempt
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


@csrf_exempt
def session_list(request):
    """
    List all sessions, or create a new session.
    """
    if request.method == "GET":
        sessions = Session.objects.all()
        serializer = SessionSerializer(sessions, many=True)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == "POST":
        data = JSONParser().parse(request)
        serializer = SessionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)


@csrf_exempt
def session_detail(request, pk):
    """
    Retrieve, update or delete a session.
    """
    try:
        session = Session.objects.get(pk=pk)
    except Session.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == "GET":
        serializer = SessionSerializer(session)
        return JsonResponse(serializer.data)

    elif request.method == "PUT":
        data = JSONParser().parse(request)
        serializer = SessionSerializer(session, data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=400)

    elif request.method == "DELETE":
        session.delete()
        return HttpResponse(status=204)


@csrf_exempt
def session_answer_list(request):
    """
    List all session answers, or create a new session answer.
    """
    if request.method == "GET":
        session_answers = SessionAnswer.objects.all()
        serializer = SessionAnswerSerializer(session_answers, many=True)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == "POST":
        data = JSONParser().parse(request)
        serializer = SessionAnswerSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)


@csrf_exempt
def session_answer_detail(request, pk):
    """
    Retrieve, update or delete a session_answer.
    """
    try:
        session_answer = SessionAnswer.objects.get(pk=pk)
    except Session.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == "GET":
        serializer = SessionAnswerSerializer(session_answer)
        return JsonResponse(serializer.data)

    elif request.method == "PUT":
        data = JSONParser().parse(request)
        serializer = SessionAnswerSerializer(session_answer, data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=400)

    elif request.method == "DELETE":
        session_answer.delete()
        return HttpResponse(status=204)


@csrf_exempt
def event_list(request):
    """
    List all events, or create a new event.
    """
    if request.method == "GET":
        events = Event.objects.all()
        serializer = EventSerializer(events, many=True)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == "POST":
        data = JSONParser().parse(request)
        serializer = EventSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)


@csrf_exempt
def event_detail(request, pk):
    """
    Retrieve, update or delete a event.
    """
    try:
        event = Event.objects.get(pk=pk)
    except Event.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == "GET":
        serializer = EventSerializer(event)
        return JsonResponse(serializer.data)

    elif request.method == "PUT":
        data = JSONParser().parse(request)
        serializer = EventSerializer(event, data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=400)

    elif request.method == "DELETE":
        event.delete()
        return HttpResponse(status=204)
