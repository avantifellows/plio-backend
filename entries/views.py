import requests
import json
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.http import response, HttpResponseBadRequest, request
from rest_framework.decorators import api_view
import pandas as pd

from plio.settings import DB_QUERIES_URL
from utils.data import convert_objects_to_df
from utils.security import hash_function
from utils.cleanup import is_valid_user_id

URL_PREFIX_GET_ALL_ENTRIES = '/get_entries'

def index(request):
    return redirect('https://player.plio.in', permanent=True)


@api_view(['GET'])
def get_df(request):
    """Returns a dataframe for all entries"""
    logging.info('Fetching all entries df')
    entries = fetch_all_entries()

    # if the returned object is not dict, it will be some variant
    # of HttpResponseNotFound, returning it if that's the case
    if not isinstance(entries, list):
        return entries

    entries_df = convert_objects_to_df(entries)
    preprocess = json.loads(request.GET.get('preprocess', 'True').lower())

    if preprocess:
        # add secret key to each entry
        entries_df['secret_key'] = entries_df['user-id'].apply(
            hash_function)

        # handle country code if not already present
        entries_df['user-id'] = entries_df['user-id'].apply(
            lambda _id: _id if len(_id) > 10 else f'91{_id}'
        )

        # remove test entries
        entries_df = remove_entries_from_test_users(entries_df, 'user-id')

        # convert msec to sec
        entries_df['watch-time'] /= 1000

    return JsonResponse(entries_df.to_dict())


# def remove_test_entries(entries_df: pd.DataFrame) -> pd.DataFrame:
#     """Removes test entries"""
#     entries_df = entries_df[~entries_df['id'].apply(is_test_plio_id)]
#     entries_df = entries_df[~entries_df['video_id'].apply(is_test_plio_video)]

#     return entries_df.reset_index(drop=True)


def fetch_all_entries():
    print('Fetching')
    response = requests.get(DB_QUERIES_URL + URL_PREFIX_GET_ALL_ENTRIES)
    if (response.status_code != 200):	
        return HttpResponseNotFound('<h1>An unknown error occurred</h1>')

    print('Done')
    return json.loads(response.json())


def remove_entries_from_test_users(
        entries_df: pd.DataFrame, entry_user_id_key: str) -> pd.DataFrame:
    """Removes test user IDs from the entries dataframe"""
    return entries_df[entries_df[entry_user_id_key].apply(
        is_valid_user_id)].reset_index(drop=True)