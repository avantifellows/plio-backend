from ivideo.settings import DB_QUERIES_URL
from typing import Dict, List
from os.path import join, splitext, basename
import requests

import boto3
import botocore
import json
import os

import datetime
from django.conf import settings

DEFAULT_BUCKET = 'plio-data'

CREATE_USER_PATH = '/create_user'

# Look in zappa_settings.json if you want to change this URL
DB_QUERIES_URL = settings.DB_QUERIES_URL

LOCAL_STORAGE_PATH = '/tmp/'
PLIOS_DB_FILE = 'all_plios.json'


def push_response_to_s3(response_data: Dict):
    """Upload response to s3"""
    response = response_data['response']

    # authenticate
    s3 = get_resource()

    # define bucket
    bucket = DEFAULT_BUCKET

    # directory where responses are saved
    save_dir = 'answers'

    # define the path where the response is saved
    file_name = "{}_{}-{}.json".format(
        response['plio-id'], response['user-id'],
        response['session-id'])

    # To handle windows' default backslash system
    file_path = join(save_dir, file_name).replace("\\", "/")

    s3.Object(bucket, file_path).put(
        Body=json.dumps(response), ContentType='application/json')

    return f"http://{DEFAULT_BUCKET}.s3.ap-south-1.amazonaws.com/{file_path}"


def get_resource(
        service_name: str = 's3', region_name: str = 'ap-south-1',
        aws_access_key_id: str = 'AKIARUBOPCTS2VKY7QQH',
        aws_secret_access_key: str ='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'):
    """Authenticates boto3 and returns and S3 resource"""

    return boto3.resource(
        service_name=service_name,
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )


def get_all_plios(
        bucket: str = DEFAULT_BUCKET, extensions: List[str] = ['.json']):
    """Returns all the plios in the specified bucket"""

    path = LOCAL_STORAGE_PATH + PLIOS_DB_FILE
    if not os.path.exists(path):
        s3 = get_resource()
        s3.Bucket(bucket).download_file(PLIOS_DB_FILE, path)

    plios = {}
    with open(path) as f:
        plios = json.load(f)

    all_plios = [] 
    # Iterate throgh 'files', convert to dict. and add extension key.
    for plio in plios:
        
        name, ext = splitext(basename(plio['key']))
        if ext in extensions:
            json_content = json.loads(plio['response'])
            video_title = json_content.get('video_title', '')
            date = plio["last_modified"]
            all_plios.append(dict({
                "plio_id": name, "details": json_content,
                "title": video_title, "created": date
            }))
    
    return all_plios


def get_session_id(
        plio_id: str, user_id: str, bucket: str = DEFAULT_BUCKET):
    """Returns the session ID for a given user-plio combination"""
    if not plio_id:
        raise ValueError('Invalid plio_id')

    if not user_id:
        return 1

    s3 = get_resource()
    s3_bucket = s3.Bucket(bucket)

    # get all entries only from bucket
    files = s3_bucket.objects.filter(
        Prefix='answers/' + plio_id + "_" + user_id, Delimiter='/')
    
    # get new session ID
    session_id = sum([1 for _ in files])
    return session_id


def create_user_profile(user_id: str, bucket_name: str = DEFAULT_BUCKET):
    params = {
        "phone": user_id
    }
    requests.post(DB_QUERIES_URL + CREATE_USER_PATH, json=params )
