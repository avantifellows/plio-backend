import ivideo
from django.http import request
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotFound

import json

from utils.avanti_s3 import get_all_ivideo_objects


def index(request):
    all_ivideos = get_all_ivideo_objects()
    all_ivideos = [ivideo for ivideo in all_ivideos if "object_id" in ivideo]
    context = {
        "all_ivideos": all_ivideos
    }

    return render(request, 'index.html', context)
    

