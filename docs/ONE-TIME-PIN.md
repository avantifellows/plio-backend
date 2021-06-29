## One Time Pin
Plio backend has inbuilt OTP functionality for users to log in with a pin generated. This document covers step by step details on how to get the login functionality in place using OTP.

### Set up AWS SNS
We support text messaging through AWS Simple Notification Service.

1. Set up an IAM user at AWS with full access to SNS. Follow this [AWS guide](https://docs.aws.amazon.com/sns/latest/dg/sns-setting-up.html#create-iam-user) to set it up.
2. Copy the AWS client id, secret and region.
3. Update your `.env` file and set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_REGION` variables from the copied values in the above step:
    ```sh
    AWS_ACCESS_KEY_ID="your_aws_key_id"
    AWS_SECRET_ACCESS_KEY="your_aws_secret_key"
    AWS_REGION="your_aws_region"
    ```
    **NOTE:** Make sure your region & country is supported by AWS SNS. [Read more here](https://docs.aws.amazon.com/sns/latest/dg/sns-supported-regions-countries.html).
4. Enable delivery logs (optional, recommeded for production)
   1. Visit the SNS dashboard and go to `Text messaging (SMS)`.
   2. Navigate to `Text messaging preferences` and click on `Edit` button.
   3. Go to `Delivery status logging` section.
   4. Set `success sample rate` to 100%.
   5. In the IAM roles, if you have already created the SNS Success feedback role, select that and skip to step 7. Otherwise click on `Create new service role`.
   6. When clicked on create new service role, next click on `Create new roles` button. It will take you to a different page.
      1. You will see IAM role are pre-selected. Inside the policy name, select the option that starts with `oneClick_`. These are the default policies.
      2. Click on `Allow` button. It should take you back to the SNS screen and you should see the new roles configured.
   7. Click on `Save changes`.
   8. Whenever a SMS will be published, you can access the logs from CloudWatch. The log group will start with `sns/`.
