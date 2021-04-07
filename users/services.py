import boto3
from plio.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION


class SnsService:
    def __init__(self):
        self.client = boto3.client(
            "sns",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )

    def publish(self, mobile, message):
        self.client.set_sms_attributes(attributes={"DefaultSMSType": "Transactional"})
        self.client.publish(
            PhoneNumber=mobile,
            Message=message,
        )
