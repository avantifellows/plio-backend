import requests
import random
from os.path import basename
from typing import Dict
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.http import response, HttpResponseBadRequest, request
from rest_framework.decorators import api_view
from plio.settings import DB_QUERIES_URL
from users.views import get_user_config, update_user_config
from utils.s3 import get_default_user_config

URL_PREFIX_GET_EXPERIMENT = '/get_experiment'


@api_view(['GET'])
def get_assignment(request):
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
    user_config = get_user_config(user_id)
    if isinstance(user_config, HttpResponseNotFound):
        user_config = get_default_user_config()

    experiment_config = user_config['experiments']

    if experiment_id in experiment_config:
        # sticky assignment - ensure that once a user is assigned
        # to a variant then they are always assigned that variant
        assignment = experiment_config[experiment_id]['assignment']
    else:
        expt_details = get_experiment(experiment_id)
        if isinstance(expt_details, HttpResponseNotFound):
            return expt_details
            
        expt_details = expt_details['details']

        distribution = {
            variant: probability for variant, probability in zip(
                expt_details['links'], expt_details['split-percentages'])
        }
        # get the random assignment
        assignment = assign_user_to_variant(distribution)
        user_config['experiments'][experiment_id] = {
            'assignment': assignment
        }
        update_user_config(user_id, user_config)
    
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


def get_experiment(experiment_id):
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


def index(request):
    return redirect('https://player.plio.in', permanent=True)