from os.path import join, basename, splitext
import json
import logging
import random
import requests
import pandas as pd
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.http import response, HttpResponseBadRequest, request
from rest_framework.decorators import api_view
from rest_framework.request import Request
from datetime import datetime

from plio.settings import DB_QUERIES_URL
import plio
from components.views import get_default_config
from users.views import get_user_config
from utils.s3 import get_session_id
from utils.data import convert_objects_to_df
from utils.video import get_video_durations_from_ids
from utils.cleanup import is_test_plio_id, is_test_plio_video
from utils.request import get_user_agent_info

URL_PREFIX_GET_PLIO = '/get_plio'
URL_PREFIX_GET_SESSION_DATA = '/get_session_data'
URL_PREFIX_GET_PLIO_CONFIG = '/get_plio_config'
URL_PREFIX_GET_ALL_PLIOS = '/get_plios'	


@api_view(['GET'])
def get_plios_list(request: Request):
    response = {
        "all_plios": get_all_plios()
    }
    return JsonResponse(response)


@api_view(['GET'])
def get_plios_df(request: Request):
    """Returns a dataframe for all plios"""	
    logging.info('Fetching all plios df')
    plios = fetch_all_plios()

    # if the returned object is not dict, it will be some variant
    # of HttpResponseNotFound, returning it if that's the case
    if not isinstance(plios, list):
        return plios

    plios_df = convert_objects_to_df(plios)

    preprocess = json.loads(request.GET.get('preprocess', 'True').lower())
    keep_test_plios = json.loads(
        request.GET.get('keep_test_plios', 'False').lower())

    if preprocess:
        # load video durations
        plios_df['video_duration'] = get_video_durations_from_ids(
            plios_df['video_id'])

        plios_df['num_questions'] = plios_df['items'].apply(
            lambda items: len([item for item in items if item['type'] == 'question']))

        if not keep_test_plios:
            # remove test plios
            plios_df = remove_test_plios(plios_df)

    return JsonResponse(plios_df.to_dict())


def remove_test_plios(plios_df: pd.DataFrame) -> pd.DataFrame:
    """Removes test plios"""
    plios_df = plios_df[~plios_df['id'].apply(is_test_plio_id)]
    plios_df = plios_df[~plios_df['video_id'].apply(is_test_plio_video)]

    return plios_df.reset_index(drop=True)


def fetch_all_plios():
    response = requests.get(DB_QUERIES_URL + URL_PREFIX_GET_ALL_PLIOS)
    if (response.status_code != 200):	
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    return json.loads(response.json())


def get_all_plios():	
    """Returns the list of all plios for the frontend"""	
    plios = fetch_all_plios()

    # if the returned object is not dict, it will be some variant
    # of HttpResponseNotFound, returning it if that's the case
    if not isinstance(plios, list):
        return plios

    all_plios = [] 	

    # Iterate through 'files', convert to dict	
    for plio in plios:	
        name, _ = splitext(basename(plio['key']))	
        json_content = json.loads(plio['response'])	
        video_title = json_content.get('video_title', '')	
        date = plio["last_modified"]	
        all_plios.append(dict({	
            "plio_id": name, "details": json_content,	
            "title": video_title, "created": date	
        }))	
    	
    return all_plios


@api_view(['GET'])
def get_plio(request: Request):
    plio_id = request.GET.get('plioId', '')
    user_id = request.GET.get('userId', '')

    if not plio_id:
        return HttpResponseNotFound('<h1>No plio ID specified</h1>')

    data = requests.get(DB_QUERIES_URL + URL_PREFIX_GET_PLIO, params={ "plio_id": plio_id})
    
    if (data.status_code == 404):
        return HttpResponseNotFound('<h1>No plio Found with this ID</h1>')
    if (data.status_code != 200):
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    plio_data = data.json()["plio"]

    questions = []
    times = []
    options = []
    for item in plio_data['items']:
        if item['type'] == 'question':
            questions.append(item['details']['text'])
            options.append(item['details']['options'])
            times.append(item['time'])

    # get the session ID
    session_id = get_session_id(plio_id, user_id)

    response = {
        'plioDetails': plio_data,
        'times': times,
        'options': options,
        'videoId': plio_data['video_id'],
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
        
        session_plio_data = session_data.json()["sessionData"]
        response['sessionData'] = session_plio_data
    
    if not user_id:
        response['userConfigs'] = {}
    else:
        response['userConfigs'] = get_user_config(user_id)

    # prepare plio config
    plio_config = prepare_plio_config(plio_id)
    
    # if the returned object is not dict, it will be some variant
    # of HttpResponseNotFound, returning it if that's the case
    if not isinstance(plio_config, dict):
        return plio_config
    
    response['plioConfig'] = plio_config

    return JsonResponse(response, status=200)


def prepare_plio_config(plio_id: str):
    """
    Fetches the specific plio-config and default-plio-config,
    if a feature F1 is present in plio-config, it will override that
    feature in default-plio-config, and return it
    """
    default_plio_config = get_default_config('plio')
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
def _get_plio_config(request: Request):
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


def get_plio_config(plio_id: str):
    """Fetches config of the specified plio from the DB"""
    plio_config = requests.get(
        DB_QUERIES_URL + URL_PREFIX_GET_PLIO_CONFIG, params={"plio_id": plio_id}
    )

    if (plio_config.status_code == 404):
        return HttpResponseNotFound(f'<h1>plio-config for plio {plio_id} not found</h1>')
    if (plio_config.status_code != 200):
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    return plio_config.json()["plio_config"]


def index(request: Request):
    """Renders home page for backend""" 
    plios = get_all_plios()

    # if the returned object is not dict, it will be some variant
    # of HttpResponseNotFound, returning it if that's the case
    if not isinstance(plios, list):
        return plios

    return render(request, 'index.html', {
        "all_plios": plios
    })


def redirect_home(request: Request):
    """Redirect to frontend home"""
    return redirect('https://player.plio.in', permanent=True)


def redirect_plio(request: Request, plio_id: str):
    """Redirect to frontend plio page"""
    return redirect(
        f'https://player.plio.in/#/play/{plio_id}', permanent=True)