## Zappa Settings

This guide explains all the available configurations in your `zappa_settings.json` file so that you can configure your environments accordingly.

#### `environment` (dev, prod or local)
The type of environment you are configuring zappa for:
1. `prod` - for production environment
2. `dev` - for staging/testing environment
3. `local` - for local development

#### `django_settings`
The settings file in your Django app. For this project, keep it `plio.settings`. Not required in local development.

#### `profile_name`
Your zappa profile name configured at AWS. Not required in local development.

#### `project_name`
Your zappa project name configured at AWS. Not required in local development.

#### `runtime`
Your zappa project name configured at AWS. Not required in local development.

#### `s3_bucket`
The S3 bucket that zappa will utilize. Not required in local development.

#### `aws_region`
The AWS server region. Not required in local development.

#### `environment_variables`
These are the environment variables passed on to the Django app for various functionalities.

1. `DJANGO_ENV` - Env type for Django.
   1. `prod` for prod environment
   2. `staging` for dev environment
   3. `local` for local environment
2. `STATIC_BUCKET` - S3 bucket for static assets.
3. `DB_QUERIES_URL` - URL for `db_queries` repository hosting. Soon to be deprecated.
4. `CMS_TOKEN` - Secret token for Avanti's [Content Management System](http://cms.peerlearning.com) - if you plan to use it, you'll need to ask for access from the admins.
5. `DATABASE_HOST` - Database server host URL. For local development, use `localhost`.
6. `DATABASE_PORT` - Port on which database is running. Default `5432` for local installation.
7. `DATABASE_NAME` - Name of your database.
8. `DATABASE_USER` - Database username.
9. `DATABASE_PASSWORD` - Password for database username.
