from os.path import join, basename, splitext
import os
import json
from typing import Dict
import random
import requests
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.http import response, HttpResponseBadRequest, request
from rest_framework.decorators import api_view
from device_detector import SoftwareDetector, DeviceDetector

from plio.settings import DB_QUERIES_URL
import plio
from users.views import get_user_config
from utils.s3 import push_response_to_s3, \
    get_session_id

URL_PREFIX_GET_PLIO = '/get_plio'
URL_PREFIX_GET_SESSION_DATA = '/get_session_data'
URL_PREFIX_GET_ALL_PLIOS = '/get_plios'


@api_view(['POST'])
def update_response(request):
    '''Push student response JSON to s3

    request -- A JSON containing the student response
                and meta data

    request:{
        'response' : {
            'answers' : list of strings,
            'watch-time' : integer,
            'user-id' : string,
            'plio-id' : string,
            'session-id' : integer,
            'source' : string,
            'retention' : list of integers,
            'has-video-played' : integer,
            'journey' : list of dicts,
            'user_agent' : Object
        }
    }
    '''
    request.data['response']['user_agent'] = get_user_agent_info(request)
    file_path = push_response_to_s3(request.data)

    return JsonResponse({
        'path': file_path
    }, status=200)


@api_view(['GET'])
def get_plios_list(request):
    
    all_plios = get_all_plios()
    response = {
        "all_plios": all_plios
    }
    return JsonResponse(response)


def get_all_plios():
    """Returns all plios information which the frontend can consume"""
    
    data = requests.get(DB_QUERIES_URL + URL_PREFIX_GET_ALL_PLIOS)
    if (data.status_code != 200):
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    plios = json.loads(data.json())
    all_plios = [] 
    # Iterate throgh 'files', convert to dict
    for plio in plios:
        name, ext = splitext(basename(plio['key']))
        json_content = json.loads(plio['response'])
        video_title = json_content.get('video_title', '')
        date = plio["last_modified"]
        all_plios.append(dict({
            "plio_id": name, "details": json_content,
            "title": video_title, "created": date
        }))
    
    return all_plios


@api_view(['GET'])
def get_plio(request):
    plio_id = request.GET.get('plioId', '')
    user_id = request.GET.get('userId', '')

    if not plio_id:
        return HttpResponseNotFound('<h1>No plio ID specified</h1>')

    data = requests.get(DB_QUERIES_URL + URL_PREFIX_GET_PLIO, params={ "plio_id": plio_id})
    
    if (data.status_code == 404):
        return HttpResponseNotFound('<h1>No plio Found with this ID</h1>')
    if (data.status_code != 200):
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    jsondata = data.json()["plio"]

    questions = []
    times = []
    options = []
    for question in jsondata['questions']['questions']:
        q = question['question']
        questions.append(q['text'])
        options.append(q['options'])
        times.append(question['time'])

    # get the session ID
    session_id = get_session_id(plio_id, user_id)

    response = {
        'plioDetails': jsondata,
        'times': times,
        'options': options,
        'videoId': jsondata['video_id'],
        'plioId': plio_id,
        'userAgent': get_user_agent_info(request),
        'sessionId': session_id,
        'sessionData': ''
    }

    # get previous session data if it exists
    if session_id != 0:
        session_data = requests.get(
            DB_QUERIES_URL + URL_PREFIX_GET_SESSION_DATA, params={
                "plio_id": plio_id,
                "user_id": user_id,
                "session_id": session_id-1
            })

        if (session_data.status_code == 404):
            return HttpResponseNotFound('<h1>No session found for this user-plio combination</h1>')
        if (session_data.status_code != 200):
            return HttpResponseNotFound('<h1>An unknown error occurred in getting the session data</h1>')
        
        session_jsondata = session_data.json()["sessionData"]
        response['sessionData'] = session_jsondata
    
    if not user_id:
        config_data = {}
    else:
        config_data = get_user_config(user_id)

    response['configData'] = config_data

    return JsonResponse(response, status=200)


def get_user_agent_info(request):
    """Get User-Agent information: browser, OS, device"""
    browser_info = request.META['HTTP_USER_AGENT']

    software_info = SoftwareDetector(browser_info).parse()
    device_info = DeviceDetector(browser_info).parse()

    if 'JioPages' in browser_info:
        browser_name = 'JioPages'
    else:
        browser_name = software_info.client_name()

    user_agent_info = {
        'os':  {
            'family':  device_info.os_name(),
            'version': device_info.os_version()
        },
        'device': {
            'family':  device_info.device_brand_name(),
            'version': device_info.device_model(),
            'type': device_info.device_type()
        },
        'browser': {
            'family': browser_name,
            'version': software_info.client_version()
        }
    }

    return user_agent_info


def index(request):
    """Renders home page for backend""" 
    return render(request, 'index.html', {"all_plios": get_all_plios()})


def redirect_home(request):
    """Redirect to frontend home"""
    return redirect('https://player.plio.in', permanent=True)


def redirect_plio(request, plio_id):
    """Redirect to frontend plio page"""
    return redirect(
        f'https://player.plio.in/#/play/{plio_id}', permanent=True)
