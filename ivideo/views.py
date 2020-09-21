from django.http import request
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotFound

import json

from utils.avanti_s3 import get_all_ivideo_objects


def index(request):
    all_ivideos = get_all_ivideo_objects()

    context = {
        "all_ivideos": all_ivideos
    }

    return render(request, 'index.html', context)
    

