from os.path import join, basename
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
from utils.s3 import get_all_plios, push_response_to_s3, \
    get_session_id

URL_PREFIX_GET_PLIO = '/get_plio'
URL_PREFIX_GET_SESSION_DATA = '/get_session_data'
URL_PREFIX_GET_DEFAULT_COMPONENT_CONFIG = '/get_default_component_config'
URL_PREFIX_GET_PLIO_CONFIG = '/get_plio_config'
URL_PREFIX_GET_COMPONENT_FEATURES = '/get_component_features'


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

    # prepare plio config
    plio_config = prepare_plio_config(plio_id)
    if not isinstance(plio_config, dict):
        return plio_config
    
    response['plioConfig'] = plio_config

    return JsonResponse(response, status=200)


@api_view(['GET'])
def _get_component_features(request):
    component_type = request.GET.get('type', '')

    if not component_type:
        return HttpResponseNotFound('<h1>No component type specified</h1>')

    component_features = get_component_features(component_type)

    if not isinstance(component_features, dict):
        return component_features
    
    return JsonResponse(component_features, status=200)


def get_component_features(component_type):
    """Returns the specific component-features JSON after fetching it from S3"""

    data = requests.get(
        DB_QUERIES_URL + URL_PREFIX_GET_COMPONENT_FEATURES, params={
            "type": component_type
        }
    )

    if (data.status_code == 404):
        return HttpResponseNotFound(f'<h1>{component_type} features not found</h1>')
    if (data.status_code != 200):
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    return data.json()["value"]


def prepare_plio_config(plio_id: str):
    """
    Fetches the specific plio-config and default-plio-config,
    if a feature F1 is present in plio-config, it will override that
    feature in default-plio-config, and return it
    """
    default_plio_config = get_default_component_config('plio')
    if not isinstance(default_plio_config, dict):
        return default_plio_config

    current_plio_config = get_plio_config(plio_id)
    if not isinstance(current_plio_config, dict):
        return current_plio_config

    current_plio_config = current_plio_config.get('player', '')

    if not current_plio_config:
        return default_plio_config

    for feature, details in current_plio_config.items():
        if feature in default_plio_config['player']:
            default_plio_config['player'][f'{feature}'] = details
    
    return default_plio_config


@api_view(['GET'])
def _get_default_component_config(request):
    """
    params: type (REQUIRED)
    example: /get_default_component_config
    """
    component_type = request.GET.get('type', '')
    if not component_type:
        return HttpResponseNotFound('<h1>No component type specified</h1>')
    
    default_component_config = get_default_component_config(component_type)

    if not isinstance(default_component_config, dict):
        return default_component_config
    
    return JsonResponse(default_component_config, status=200)


def get_default_component_config(component_type: str):
    """Fetches the default component config from the DB"""
    default_component_config = requests.get(
        DB_QUERIES_URL + URL_PREFIX_GET_DEFAULT_COMPONENT_CONFIG, params={"type" : component_type}
    )

    if (default_component_config.status_code != 200):
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    return default_component_config.json()["value"]


@api_view(['GET'])
def _get_plio_config(request):
    """
    params: plioId (REQUIRED)
    example: /get_plio_config?plioId=aAsdnq23asd
    """
    plio_id = request.GET.get('plioId', '')
    if not plio_id:
        return HttpResponseNotFound('<h1>No plio ID specified</h1>')
    
    plio_config = get_plio_config(plio_id)
    if not isinstance(plio_config, dict):
        return plio_config
    
    return JsonResponse(plio_config, status=200)


def get_plio_config(plio_id):
    """Fetches config of the specified plio from the DB"""
    plio_config = requests.get(
        DB_QUERIES_URL + URL_PREFIX_GET_PLIO_CONFIG, params={"plio_id": plio_id}
    )

    if (plio_config.status_code == 404):
        return HttpResponseNotFound(f'<h1>plio-config for plio {plio_id} not found</h1>')
    if (plio_config.status_code != 200):
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    return plio_config.json()["plio_config"]


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
