from os.path import join
import json
from django.http import response
from django.http import HttpResponseBadRequest, request
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound
from rest_framework.decorators import api_view
from device_detector import SoftwareDetector, DeviceDetector

import ivideo
from utils.s3 import get_all_plios, get_object, push_response_to_s3, \
    get_session_id, create_user_profile


@api_view(['POST'])
def update_response(request):
    '''Push student response JSON to s3

    request -- A JSON containing the student response
                and meta data

    request:{
        'response' : {
            'answers' : list of strings,
            'options' : list of lists of string,
            'watch-time' : integer,
            'source' : string,
            'retention' : list of integers,
            'user_agent' : Object
        },
        'meta' : {
            'object_id': string,
            'student_id': string
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

    data = get_object(f'videos/{plio_id}.json')
    if data is None:
        return HttpResponseNotFound('<h1>Plio not found</h1>')

    jsondata = json.loads(data)

    questions = []
    times = []
    options = []
    for question in jsondata['questions']['questions']:
        q = question['question']
        questions.append(q['text'])
        options.append(q['options'])
        times.append(question['time'])

    # create user profile if it does not exist
    create_user_profile(user_id)

    # get the session ID
    session_id = get_session_id(plio_id, user_id)

    response = {
        'plioDetails': jsondata,
        'times': times,
        'options': options,
        'videoId': jsondata['video_id'],
        'plioId': plio_id,
        'userAgent': get_user_agent_info(request),
        'sessionId': session_id
    }

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
