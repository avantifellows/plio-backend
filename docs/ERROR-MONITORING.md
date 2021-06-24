## Error Monitoring

If you're setting up Plio for staging or production, you may also wish to capture errors faced by users in real-time. For that purpose, Plio uses [Sentry.io](https://sentry.io/) for real-time error monitoring and reporting.

### Pre-requisites
1. Create an account at Sentry.
2. Set up your organization.
3. Create a new Django project. Name it `plio-backend`.


### Enable error logging
1. Set up env variable for `SENTRY_DSN`. You can get the value of DSN for your projects from `Project Settings > SDK Setup > Client Keys (DSN)`
2. Make sure your `APP_ENV` is either 'staging' or 'production'.
3. Trigger an error by adding the following line in your `urls.py` file:
    ```py
    from django.urls import path
    def trigger_error(request):
        division_by_zero = 1 / 0

    urlpatterns = [
        path('trigger-error/', trigger_error),
        # other paths
    ]
    ```
4. You should now see the error at your Sentry dashboard as well from `Issues` tab.

### Enable reporting
By default, Sentry sends error reports to your inbox. However, you may prefer other channels to receive error notifications.

At Plio, we use Discord to receive real-time alerts using Sentry Webhooks. If you're also using Discord, or a different tool that supports webhooks, follow the steps below to start receiving alerts:
1. Create a new channel at Discord where you want to receive the alerts. Then, enable the webhook and copy webhook url. `Channel settings > Integrations > Webhook`
2. Create a SentryDiscord webhook.
   1. Visit [this page at SentryDiscord.dev](https://sentrydiscord.dev/create).
   2. Paste the Discord webhook that you copied in the first step.
   3. Click on create.
   4. You will receive a new webhook. Copy and store it somewhere. We'll use it later.
3. Go to `Integrations` for your organization from `Settings > Integrations`
4. Search for `Webhooks` and click on `Add to project`.
5. Select your project.
5. Enter the SentryDiscord webhook url from step 2 inside the `Callback URLs` textbox.
6. Click `Save changes`.
7. Click `Enable Plugin`.
8. Next, go to `Alerts`. By default you may see an alert named `Send a notification for new issues`. If yes, you can skip the create alert step below and got to edit existing alert.
9. Create a new Alert
   1. Click on `Create Alert Rule`.
   2. In the select alert section, select `Issues` inside the `Errors` heading.
   3. Click on `Set Conditions`.
   4. `Environment` to be "All Environments".
   5. Set the Alert name to "Send a notification for new issues"
   6. Move to Set Conditions section.
   7. For `WHEN`, select "A new issue is created".
   8. For `IF`, leave it as default (no filters).
   9. For `THEN`, add two options.
      1. `Send a notification` and select `Issue Owners` .
      2. `Send a notification via an integration` and select `WebHooks`.
   10. Set action interval as per your needs.
10. Edit existing alert - use this if you want to edit existing alert
    1. Move to Set Conditions section.
    2. For `THEN`, make sure you have the `Send a notification via an integration` option configured with `WebHooks`.
11. All set. Trigger an error in your app and you should see the error coming to your Discord channel!
