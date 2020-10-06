from django.http import request
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotFound

import json

from utils.avanti_s3 import get_object


def index(request):
    return HttpResponse("Hello, world. You're at the player index.")


def watch_ivideo(request, ivideo_id):
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

    context = {
        'ivideo_details': jsondata,
        'times': times,
        'questions_list': questions,
        'set_of_options': options,
        'video_id': jsondata['video_id'],
        'ivideo_id': ivideo_id
    }
    return render(request, 'ivideo_player/watch_ivideo.html', context)


def edit_ivideo(request, ivideo_id):
    return HttpResponse("You're asking to edit ivideo: " + ivideo_id)
