import boto3
from botocore.exceptions import ClientError
import json

# NOTE: public authentication details


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
