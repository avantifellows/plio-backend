## One Time Pin
Plio backend has inbuilt OTP functionality for users to log in with a pin generated. This document covers step by step details on how to get the login functionality in place using OTP.

### Set up AWS SNS
We support text messaging through AWS Simple Notification Service.

1. Set up an IAM user at AWS with full access to SNS. Follow this [AWS guide](https://docs.aws.amazon.com/sns/latest/dg/sns-setting-up.html#create-iam-user) to set it up.
2. Copy the AWS client id, secret and region.
3. Update your `zappa_settings.json` file and set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_REGION` variables from the copied values in the above step:
    ```json
    {
        "AWS_ACCESS_KEY_ID": "your_aws_key_id",
        "AWS_SECRET_ACCESS_KEY": "your_aws_secret_key",
        "AWS_REGION": "your_aws_region"
    }
    ```
    **NOTE:** Make sure your region & country is supported by AWS SNS. [Read more here](https://docs.aws.amazon.com/sns/latest/dg/sns-supported-regions-countries.html).
