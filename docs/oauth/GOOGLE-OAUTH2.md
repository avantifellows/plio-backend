## Google OAuth2
Plio backend uses [DRF Social OAuth2](https://github.com/RealmTeam/django-rest-framework-social-oauth2) Vue package to support various social media sign in functionalities. This document covers step by step details on how to get the sign-in functionality running.

  - [Set up Google OAuth2 Credentials](#set-up-google-oauth2-credentials)
  - [Set up Plio Backend API](#set-up-plio-backend-api)
  - [Testing](#testing)
  - [In case of failure](#in-case-of-failure)
  - [Additional Help](#additional-help)

### Set up Google OAuth2 Credentials
1. Use the [Plio frontend Google-OAuth2 guide](https://github.com/avantifellows/plio-frontend/blob/master/docs/oauth/GOOGLE-OAUTH2.md#set-up-google-oauth2-credentials) to configure Google Developer Console and get the **Client ID** and **Client Secret**.
2.  Update your `zappa_settings.json` file and set `GOOGLE_OAUTH2_CLIENT_ID` and `GOOGLE_OAUTH2_CLIENT_SECRET` variables from the copied values in the above step:
    ```json
    {
    "GOOGLE_OAUTH2_CLIENT_ID": "your_client_id",
    "GOOGLE_OAUTH2_CLIENT_SECRET": "your_client_secret"
    }
    ```


### Set up Plio Backend API

**Note**: If you're using the Plio backend, make sure you follow the steps mentioned in the Backend API setup guide.

After your Backend API is correctly configured, retrieve the client id and client secret. Please note that you will now have two pairs of client id and secret:
1. From Google Developer Console
2. From Plio Backend API

Update your `.env` file with the Plio backend client id and secret
```sh
VUE_APP_BACKEND_API_CLIENT_ID='plio_backend_client_id'
VUE_APP_BACKEND_API_CLIENT_SECRET='plio_backend_client_secret'
```

### Testing
Restart the frontend server and navigate to the login page. Now you should see the `Google Sign-in` functionality should be working as expected.


### In case of failure
You can check the brower console to check errors which occur during initialization. The most of errors are due to inproper setting of Google OAuth2 credentials setting in Google Developer Console. After changing the settings, you have to do hard refresh to clear your caches.

### Additional Help
1. [Google API Client Libraries : Methods and Classes](https://github.com/google/google-api-javascript-client)
2. If you are curious of how the entire Google sign-in flow works, please refer to the diagram below
![Google Sign-in Flow](https://developers.google.com/identity/sign-in/web/server_side_code_flow.png)
