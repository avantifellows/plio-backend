from plio.settings import DB_QUERIES_URL
from typing import Dict, List, Any
from os.path import splitext, basename
import requests

import boto3
import botocore
import json
import os
import gzip

import datetime
from django.conf import settings

DEFAULT_BUCKET = "plio-data"
CREATE_USER_PATH = "/create_user"
GET_DEFAULT_USER_CONFIG_PATH = "/get_default_user_config"

# Look in zappa_settings.json if you want to change this URL
DB_QUERIES_URL = settings.DB_QUERIES_URL


def get_resource(
    service_name: str = "s3",
    region_name: str = "ap-south-1",
    aws_access_key_id: str = "AKIARUBOPCTS2VKY7QQH",
    aws_secret_access_key: str = "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",
):
    """Authenticates boto3 and returns and S3 resource"""

    return boto3.resource(
        service_name=service_name,
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )


def get_session_id(plio_id: str, user_id: str, bucket: str = DEFAULT_BUCKET):
    """Returns the session ID for a given user-plio combination"""
    if not plio_id:
        raise ValueError("Invalid plio_id")

    # TODO: for older plio-user entries, have to add a file with session id "0"
    # which will be identical to the file with session id "1"
    if not user_id:
        return 0

    s3 = get_resource()
    s3_bucket = s3.Bucket(bucket)

    # get all entries only from bucket
    files = s3_bucket.objects.filter(
        Prefix="answers/" + plio_id + "_" + user_id, Delimiter="/"
    )

    # get new session ID
    session_id = sum([1 for _ in files])
    return session_id


def create_user_profile(user_id: str, bucket_name: str = DEFAULT_BUCKET):
    params = {"phone": user_id}
    requests.post(DB_QUERIES_URL + CREATE_USER_PATH, json=params)


def get_default_user_config():
    response = requests.get(DB_QUERIES_URL + GET_DEFAULT_USER_CONFIG_PATH)
    return json.loads(response.json())
