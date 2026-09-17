import boto3
from django.conf import settings


class SnsService:
    def __init__(self):
        self.client = boto3.client(
            "sns",
            region_name=settings.AWS_REGION or None,
        )

    def publish(self, mobile, message):
        self.client.publish(
            PhoneNumber=mobile,
            Message=message,
            MessageAttributes={
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",
                }
            },
        )
