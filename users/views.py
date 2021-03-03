import requests
import json
import math
import logging
import pandas as pd
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.http import response, HttpResponseBadRequest, request
from rest_framework.decorators import api_view
from plio.settings import DB_QUERIES_URL

from utils.s3 import create_user_profile
from utils.data import convert_objects_to_df
from utils.cleanup import is_valid_user_id
from utils.security import hash_function

URL_PREFIX_GET_USER_CONFIG = '/get_user_config'
URL_PREFIX_UPDATE_USER_CONFIG = '/update_user_config'
URL_PREFIX_GET_ALL_USERS = '/get_users'


# Create your views here.
def index(request):
    return redirect('https://player.plio.in', permanent=True)


def get_user_config(user_id):
    """Returns the user config for the given user ID"""
    if not user_id:
        return HttpResponseNotFound('<h1>No user ID specified</h1>')
    
    data = requests.get(
        DB_QUERIES_URL + URL_PREFIX_GET_USER_CONFIG, params={
            "user_id": get_valid_user_id(user_id)
        })

    if (data.status_code == 404):
        return HttpResponseNotFound('<h1>No config found for this user ID</h1>')
    if (data.status_code != 200):
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')
    
    return data.json()["user_config"]


@api_view(['GET'])
def _get_user_config(request):
    user_id = request.GET.get('user-id', '')
    config = get_user_config(user_id)
    if not isinstance(config, dict):
        return config

    return JsonResponse(config, status=200)


def update_user_config(user_id, config_data):
    """Function to update user config given user Id and config"""
    params = {
        'user_id': get_valid_user_id(user_id),
        'configs': config_data
    }

    requests.post(
        DB_QUERIES_URL + URL_PREFIX_UPDATE_USER_CONFIG, json=params)
    return JsonResponse({
        'status': 'Success! Config updated'
    }, status=200)


@api_view(['POST'])
def _update_user_config(request):
    """Update the user config"""
    user_id = request.data.get('user-id', '')
    config_data = request.data.get('configs', '')

    if not user_id:
        return HttpResponseNotFound('<h1>No user-id specified</h1>')
    if not config_data:
        return HttpResponseNotFound('<h1>No tutorial data specified</h1>')
    
    return update_user_config(user_id, config_data)


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


@api_view(['GET'])
def get_df(request):
    """Returns a dataframe for all users"""	
    users = fetch_all_users()

    # if the returned object is not dict, it will be some variant
    # of HttpResponseNotFound, returning it if that's the case
    if not isinstance(users, list):
        return users

    users_df = convert_objects_to_df(users)

    preprocess = json.loads(request.GET.get('preprocess', 'True').lower())

    if preprocess:
        # add secret key to each user
        users_df['secret_key'] = users_df['id'].apply(
            hash_function)

        # remove bad user IDs
        users_df = remove_test_users(users_df)

        users_df['block'] = users_df['address'].apply(
            lambda address: address['block'] if isinstance(
                address, dict) else 'unknown'
        )

        users_df['district'] = users_df['address'].apply(
            lambda address: address['district'] if isinstance(
                address, dict) else 'unknown'
        )

        users_df['school-name'] = users_df['school'].apply(
            lambda school: school['name'] if isinstance(
                school, dict) else 'unknown'
        )

        users_df['school-code'] = users_df['school'].apply(
            lambda school: school['code'].split('.')[0] if not (
                isinstance(school, float) and math.isnan(school)
            ) else 'unknown'
        )

        users_df['grade'] = users_df['grade'].apply(
            lambda grade: grade.split('.')[0] if not (
                isinstance(grade, float) and math.isnan(grade)
            ) else 'unknown'
        )

        users_df.drop(columns=['address', 'school'], inplace=True)

    return JsonResponse(users_df.to_dict())


def fetch_all_users():
    response = requests.get(DB_QUERIES_URL + URL_PREFIX_GET_ALL_USERS)
    if (response.status_code != 200):
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    return json.loads(response.json())


def remove_test_users(users_df: pd.DataFrame) -> pd.DataFrame:
    """Removes known test users based on their IDs"""
    # currently only ensures that the user ID should be non-empty
    return users_df[users_df['id'].apply(
        is_valid_user_id)].reset_index(drop=True)
