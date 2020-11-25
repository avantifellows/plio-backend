from typing import Dict, List
from os.path import join, splitext, basename
import requests

import boto3
import botocore
import json

import urllib.request
import urllib
import datetime

DEFAULT_BUCKET = 'plio-data'
DB_QUERIES_URL = 'https://db-queries.plio.in/'
GET_USER_PATH = 'get_student?phone='


def get_video_title(video_id: str):
    """Gets video title from YouTube"""
    params = {
        "format": "json",
        "url": "https://www.youtube.com/watch?v=%s" % video_id
    }
    url = "https://www.youtube.com/oembed"
    query_string = urllib.parse.urlencode(params)
    url = url + "?" + query_string

    with urllib.request.urlopen(url) as response:
        response_text = response.read()
        data = json.loads(response_text.decode())
    return data["title"]


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


def get_object(key: str, bucket: str = DEFAULT_BUCKET):
    """Returns the object data for a given key in the given bucket"""
    s3 = get_resource()
    try:
        obj = s3.Object(bucket, key)
        return obj.get()['Body'].read().decode('utf-8')
    except:
        return None


def get_all_plios(
        bucket: str = DEFAULT_BUCKET, extensions: List[str] = ['.json']):
    """Returns all the plios in the specified bucket"""
    s3 = get_resource()
    s3_bucket = s3.Bucket(bucket)

    # get all plios only from the bucket
    files = s3_bucket.objects.filter(Prefix='videos/', Delimiter='/')
    # create empty list for final information
    matching_files = []

    # Iterate throgh 'files', convert to dict. and add extension key.
    for file in files:
        name, ext = splitext(basename(file.key))
        if ext in extensions:
            json_content = json.loads(
                s3.Object(bucket, file.key).get()['Body'].read().decode(
                    'utf-8'))
            video_title = get_video_title(json_content["video_id"])
            date = datetime.datetime.strftime(
                file.last_modified, "%Y-%m-%d")
            matching_files.append(dict({
                "plio_id": name, "details": json_content,
                "title": video_title, "created": date
            }))
    
    return matching_files


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
    files = s3_bucket.objects.filter(Prefix='answers/', Delimiter='/')
    # create empty list for final information
    session_id = 1

    # Iterate throgh 'files', convert to dict. and add extension key.
    for file in files:
        # only retain entries for the given Plio ID and user ID combination
        if plio_id in file.key and user_id in file.key:
            session_id += 1

    return session_id


def create_user_profile(user_id: str, bucket_name: str = DEFAULT_BUCKET):
    # handle edge case
    if user_id == 'undefined':
        return

    s3 = get_resource()

    # need to append 91 as that is what we get from WhatsApp
    user_id = '91' + user_id

    user_profile_object = s3.Object(
        bucket_name, f'users/{user_id}.json')
    try:
        user_profile_object.load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            # user profile does not exist
            user_info = {
                'phone': user_id
            }

            # check if information is present in WhatsApp DB
            db_response = requests.get(
                url = DB_QUERIES_URL + GET_USER_PATH + user_id
            ).json()

            if 'students' in db_response:
                # hard-coding to always retain only the first entry
                # for numbers with multiple entries
                user_data = db_response['students'][0]
                user_info['block'] = user_data.get('Block', '')
                user_info['district'] = user_data.get('District', '')
                user_info['name'] = user_data.get('Name', '')
                user_info['grade'] = user_data.get('Grade', '')
                user_info['school'] = {
                    'code': user_data.get('School Code', ''),
                    'name': user_data.get('School Name', '')
                }

            # create profile on S3
            user_profile_object.put(
                Body=json.dumps(user_info),
                ContentType='application/json')
