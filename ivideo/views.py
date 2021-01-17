from ivideo.settings import DB_QUERIES_URL
from os.path import join, basename
import json
from typing import Dict
import random
from django.http import response
from django.http import HttpResponseBadRequest, request
from django.http import JsonResponse
import requests
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound
from rest_framework.decorators import api_view
from device_detector import SoftwareDetector, DeviceDetector

import ivideo
from utils.s3 import get_all_plios, push_response_to_s3, \
    get_session_id, create_user_profile

URL_PREFIX_GET_PLIO = '/get_plio'
URL_PREFIX_GET_EXPERIMENT = '/get_experiment'
URL_PREFIX_GET_SESSION_DATA = '/get_session_data'
URL_PREFIX_GET_USER_CONFIG = '/get_user_config'
URL_PREFIX_UPDATE_USER_CONFIG = '/update_user_config'

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


def _update_user_config(user_id, config_data):
    """Function to update user config given user Id and config"""
    params = {
        'user_id': user_id,
        'configs': config_data
    }

    requests.post(DB_QUERIES_URL + URL_PREFIX_UPDATE_USER_CONFIG, json=params)
    return JsonResponse({
        'status': 'Success! Config updated'
    }, status=200)


@api_view(['POST'])
def login_user(request):
    '''Login given user

    request -- A JSON containing the user Id

    request:{
        'userId': user ID to be logged in
    }
    '''
    user_id = request.data.get('userId', '')

    if not user_id:
        return HttpResponseNotFound('<h1>No user ID specified</h1>')

    try:
        create_user_profile(user_id)
    except Exception as e:
        print(e)

    return JsonResponse({
        'status': 'User logged in'
    }, status=200)


@api_view(['POST'])
def update_user_config(request):
    """Update the user config"""
    user_id = request.data.get('user-id', '')
    config_data = request.data.get('configs', '')

    if not user_id:
        return HttpResponseNotFound('<h1>No user-id specified</h1>')
    if not config_data:
        return HttpResponseNotFound('<h1>No tutorial data specified</h1>')

    _update_user_config(get_valid_user_id(user_id), config_data)


@api_view(['GET'])
def get_plios_list(request):
    
    all_plios = get_all_plios()
    response = {
        "all_plios": all_plios
    }
    return JsonResponse(response)


def get_user_config(user_id):
    """Returns the user config for the given user ID"""
    if not user_id:
        return HttpResponseNotFound('<h1>No user ID specified</h1>')
    
    data = requests.get(
        DB_QUERIES_URL + URL_PREFIX_GET_USER_CONFIG, params={ "user_id": user_id })

    if (data.status_code == 404):
        return HttpResponseNotFound('<h1>No config found for this user ID</h1>')
    if (data.status_code != 200):
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')
    
    return data.json()["user_config"]


def assign_user_to_variant(distribution: Dict[str, float]) -> str:
    """Assign a user to a variant.

    :param distribution: map from variant to its probability
    :type distribution: Dict[str, float]
    """
    assert sum(distribution.values()) == 1
    user_number = random.random()  # in the interval [0, 1]
    prob_sum = 0.0
    for variant, probability in sorted(distribution.items()):
        if prob_sum <= user_number < prob_sum + probability:
            return variant
        prob_sum += probability
    return variant


def get_experiment_details(experiment_id):
    """Returns the experiment JSON associated with the given ID"""
    data = requests.get(
        DB_QUERIES_URL + URL_PREFIX_GET_EXPERIMENT,
        params={ "experiment_id": experiment_id })
    
    if (data.status_code == 404):
        return HttpResponseNotFound(
            '<h1>No experiment found for this ID</h1>')
    if (data.status_code != 200):
        return HttpResponseNotFound(
            '<h1>An unknown error occurred</h1>')
    
    return data.json()["experiment"]


@api_view(['GET'])
def get_experiment_assignment(request):
    """Get the variant of an A/B test that the user is assigned to"""
    experiment_id = request.GET.get('experimentId', '')
    user_id = request.GET.get('userId', '')

    if not experiment_id:
        return HttpResponseNotFound('<h1>No experiment ID specified</h1>')
    
    if not user_id:
        return HttpResponseNotFound('<h1>No user ID specified</h1>')

    # can remove the call to get the assignment from user config in
    # the future by setting seed = hash(experiment_id + user_id)
    # https://martin-thoma.com/bucketing-in-ab-testing/
    user_config = get_user_config(get_valid_user_id(user_id))
    if isinstance(user_config, HttpResponseNotFound):
        return user_config

    experiment_config = user_config['experiments']

    if experiment_id in experiment_config:
        # sticky assignment - ensure that once a user is assigned
        # to a variant then they are always assigned that variant
        assignment = experiment_config[experiment_id]['assignment']
    else:
        expt_details = get_experiment_details(experiment_id)
        if isinstance(expt_details, HttpResponseNotFound):
            return expt_details
            
        expt_details = expt_details['details']

        distribution = {
            variant: probability / 100 for variant, probability in zip(
                expt_details['links'], expt_details['split-percentages'])
        }
        # get the random assignment
        assignment = assign_user_to_variant(distribution)
        user_config['experiments'][experiment_id] = {
            'assignment': assignment
        }
        _update_user_config(get_valid_user_id(user_id), user_config)
    
    # separately seting plio ID although it will be the same as assignment
    # for now as we might conduct interface level changes where assignment
    # won't be the same as plio ID
    plio_id = basename(assignment)

    response = {
        'assignment': assignment,
        'config': user_config,
        'plioId': plio_id
    }

    return JsonResponse(response, status=200)


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

    # create user profile if it does not exist
    try:
        create_user_profile(user_id)
    except Exception as e:
        print(e)
    
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
    
    config_data = get_user_config(get_valid_user_id(user_id))
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


def get_valid_user_id(user_id: str, country_code: int = 91) -> str:
    """Returns the country-code prefixed user ID

    :param user_id: user Id to be checked/edited
    :type user_id: str
    :param user_id: country code to be used; defaults to 91 (India)
    :type user_id: str
    """
    if len(user_id) == 12:
        return user_id

    return f'{country_code}{user_id}'