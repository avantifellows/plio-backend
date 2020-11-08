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
from utils.avanti_s3 import get_all_ivideo_objects, get_object, push_response_to_s3


@api_view(['POST'])
def update_response(request):
    '''Push student response JSON to s3

    request -- A JSON containing the student response
                and meta data

    request:{
        'response' : {
            'answers' : list of strings,
            'questions' : list of strings,
            'options' : list of lists of string,
            'watch-time' : integer
        },
        'meta' : {
            'object_id': string,
            'student_id': string
        }
    }
    '''
    user_agent_info = get_user_agent_info(request)
    request.data['response']['user_agent'] = user_agent_info
    file_path = push_response_to_s3(request.data)

    return JsonResponse({
        'path': file_path
    }, status=200)


@api_view(['GET'])
def get_ivideos_list(request):
    all_ivideos = get_all_ivideo_objects()
    response = {
        "all_ivideos": all_ivideos
    }
    return JsonResponse(response)


@api_view(['GET'])
def get_ivideo(request):
    ivideo_id = request.GET.get('ivideo_id', '')
    if not ivideo_id:
        return JsonResponse(
            {"Error": "No Video specified"}, status=HttpResponseBadRequest)

    data = get_object(f'videos/{ivideo_id}.json')
    if data is None:
        return HttpResponseNotFound('<h1>Video not found</h1>')

    jsondata = json.loads(data)

    questions = []
    times = []
    options = []
    for question in jsondata['questions']['questions']:
        q = question['question']
        questions.append(q['text'])
        options.append(q['options'])
        times.append(question['time'])

    response = {
        'ivideo_details': jsondata,
        'times': times,
        'questions_list': questions,
        'set_of_options': options,
        'video_id': jsondata['video_id'],
        'ivideo_id': ivideo_id,
        'browser': get_user_agent_info(request)
    }

    return JsonResponse(response, status=200)


def get_user_agent_info(request):
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
    all_ivideos = get_all_ivideo_objects()
    all_ivideos = [ivideo for ivideo in all_ivideos if "object_id" in ivideo]
    context = {
        "all_ivideos": all_ivideos
    }

    return render(request, 'index.html', context)


def redirect_home(request):
    return redirect('https://player.plio.in', permanent=True)


def redirect_ivideo(request, ivideo_id):
    return redirect(
        f'https://player.plio.in/#/play/{ivideo_id}', permanent=True)
