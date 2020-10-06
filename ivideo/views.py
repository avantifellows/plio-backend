from os.path import join
from django.http import response
import ivideo
from django.http import HttpResponseBadRequest, request
from django.http import JsonResponse
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotFound
from rest_framework.decorators import api_view


import json

from utils.avanti_s3 import get_all_ivideo_objects, get_object, get_resource


@api_view(['POST'])
def update_response(request):
    print(request.data)

    meta_data = request.data['meta']
    response = request.data['response']

    # authenticate
    s3 = get_resource()

    # define bucket
    bucket = 'avanti-fellows'

    # directory where responses are saved
    save_dir = 'answers'

    # define the path where the response is saved
    file_name = f"{meta_data['object_id']}_{meta_data['student_id']}.json"
    file_path = join(save_dir, file_name)

    s3.Object(bucket, file_path).put(Body=json.dumps(response))
    return JsonResponse({
        'path': f"http://avanti-fellows.s3.ap-south-1.amazonaws.com/{file_path}"
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
        'ivideo_id': ivideo_id
    }

    return JsonResponse(response, status=200)


def index(request):
    all_ivideos = get_all_ivideo_objects()
    all_ivideos = [ivideo for ivideo in all_ivideos if "object_id" in ivideo]
    context = {
        "all_ivideos": all_ivideos
    }

    return render(request, 'index.html', context)
