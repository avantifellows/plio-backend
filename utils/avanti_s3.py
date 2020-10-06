from os.path import join

import boto3
from botocore.exceptions import ClientError
import json

# NOTE: public authentication details


def push_response_to_s3(response_data):
    print(response_data)
    meta_data = response_data['meta']
    response = response_data['response']

    # authenticate
    s3 = get_resource()

    # define bucket
    bucket = 'avanti-fellows'

    # directory where responses are saved
    save_dir = 'answers'

    # define the path where the response is saved
    file_name = f"{meta_data['object_id']}_{meta_data['student_id']}.json"

    # To handle windows' default backslash system
    file_path = join(save_dir, file_name).replace("\\","/")

    s3.Object(bucket, file_path).put(Body=json.dumps(response), ContentType='application/json')

    print(file_path)
    print(response)

    return f"http://avanti-fellows.s3.ap-south-1.amazonaws.com/{file_path}"

def get_resource(
        service_name='s3', region_name='ap-south-1',
        aws_access_key_id='AKIAQHKYBVIIKK3LUGF6',
        aws_secret_access_key='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'):
    """Authenticates boto3"""

    return boto3.resource(
        service_name=service_name,
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )


def get_object(key, bucket="avanti-fellows"):
    s3 = get_resource()
    try:
        obj = s3.Object(bucket, key)
        return obj.get()['Body'].read().decode('utf-8')
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
    return None


def get_all_ivideo_objects(bucket='avanti-fellows', extensions=['json']):
    s3 = get_resource()
    s3_bucket = s3.Bucket(bucket)

    # get all files information from buket
    files = s3_bucket.objects.filter(Prefix='videos/', Delimiter='/')
    # create empty list for final information
    matching_files = []

    # Iterate throgh 'files', convert to dict. and add extension key.
    for file in files:
        ext = file.key.split('.')[-1]
        name = file.key.split('/')[-1].split('.')[0]
        if ext in extensions:
            try:
                json_content = json.loads(
                    s3.Object(bucket, file.key).get()['Body'].read().decode(
                        'utf-8'))
                matching_files.append(dict({
                    "object_id": name, "details": json_content
                }))
            except e:
                pass

    return matching_files
