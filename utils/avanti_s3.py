import boto3
from botocore.exceptions import ClientError

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
        print(obj)
        return obj.get()['Body'].read().decode('utf-8') 
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
    return None
    