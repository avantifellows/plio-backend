## Environment variables

This guide explains all the available configurations in your `.env` file so that you can configure your environments accordingly.

### Django settings
#### `APP_ENV`
Environment mode for the app. Possible values are: local, staging or production.

#### `SECRET_KEY`
Used by Django. It should be a secret value and shouldn't be added to git.

You can create a secret key from this website: https://djecrety.ir/

For more details, visit [Django official documentation on setting a secret key](https://docs.djangoproject.com/en/3.2/ref/settings/#std:setting-SECRET_KEY).

#### `DEBUG`
Debug mode on or off. Possible values are `True` and `False`. Do not set to true on production environments.

### Database settings
#### `DB_ENGINE`
Database engine for Plio. It should always be `django_tenants.postgresql_backend` as added in example env. However, if you wish to add your own implementation, feel free to change it.

#### `DB_HOST`
The database host.
1. If you're using Docker, the db host should be same as the dockerized database service mentioned in `docker-compose.yml` file (which is equal to `db`). If you want to connect to the docker database directly, use "localhost" as database host in connection settings.
2. If you're using a remote database, set it accordingly.

#### `DB_NAME`
The name of the database.
1. Docker - Docker automatically creates a database based on the value you've configured against this variable. Feel free to modify if you need a different database name.
2. Remote - Set it to your remote database name.

#### `DB_PORT`
The port for the database.
1. Docker - Docker automatically runs the database server on this port and exposes it for external connections also. Feel free to modify if you want a different port.
2. Remote - Set it to your remote database port.

#### `DB_USER`
The database user.
1. Docker - Docker automatically creates the db user based on value you've configured against this variable. Feel free to modify if you want a different user name.
2. Remote - Set it to your remote database user.

#### `DB_PASSWORD`
The password for the database user.
1. Docker - Docker automatically creates the db user's password based on value you've configured against this variable. Feel free to modify if you want a different user name.
2. Remote - Set it to your remote database user's password.


### Web server
#### `APP_PORT`
Port on which you want your docker app to run and expose.

### Google OAuth2
Read more about configuring Google OAuth2 functionality from our [Google OAuth guide](oauth/GOOGLE-OAUTH2.md).

#### `GOOGLE_OAUTH2_CLIENT_ID`
OAuth2 client id from Google. Required for Google Sign in functionality.

#### `GOOGLE_OAUTH2_CLIENT_SECRET`
OAuth2 client secret from Google. Required for Google Sign in functionality.

### AWS
AWS credentials are needed for One Time Pin functionality for user logins. Read more about configuring AWS credentials for OTP functionality from our [OTP guide](ONE-TIME-PIN.md).
#### `AWS_ACCESS_KEY_ID`
AWS access key ID.

#### `AWS_SECRET_ACCESS_KEY`
AWS secret access key.

#### `AWS_REGION`
Region of the AWS IAM user.

### Plio CMS
#### `CMS_TOKEN`
Secret token for Avanti's [Content Management System](http://cms.peerlearning.com) - if you plan to use it, you'll need to ask for access from the admins.
