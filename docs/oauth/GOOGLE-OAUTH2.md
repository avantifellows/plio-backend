## Google OAuth2
Plio backend uses [DRF Social OAuth2](https://github.com/RealmTeam/django-rest-framework-social-oauth2) package to support various social media sign in functionalities. This document covers step by step details on how to get the sign-in functionality running.

  - [Set up Google OAuth2 Credentials](#set-up-google-oauth2-credentials)
  - [Set up API client credentials](#set-up-api-client-credentials)

### Set up Google OAuth2 Credentials
1. Use the [Plio frontend Google-OAuth2 guide](https://github.com/avantifellows/plio-frontend/blob/master/docs/oauth/GOOGLE-OAUTH2.md#set-up-google-oauth2-credentials) to configure Google Developer Console and get the **Client ID** and **Client Secret**.
2.  Update your `.env` file and set `GOOGLE_OAUTH2_CLIENT_ID` and `GOOGLE_OAUTH2_CLIENT_SECRET` variables from the copied values in the above step:
    ```sh
    GOOGLE_OAUTH2_CLIENT_ID="your_client_id"
    GOOGLE_OAUTH2_CLIENT_SECRET="your_client_secret"
    ```

### Set up API client credentials
Refer to the REST API guide to [create API client credentials](../REST-API.md/#creating-api-credentials) from the Django Admin Dashboard.
