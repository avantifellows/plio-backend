Plio
====

## Zappa

We are using [zappa](https://github.com/zappa/Zappa) to deploy to Lambda.

You have to get set up with zappa credentials. Ask whoever is responsible (Pritam) how to do this.

Once you do this: inside the folder, create a virtual environment with python3

```
python3 -m venv zappa_env
pip install -r requirements.txt
```
### Testing

```
export DJANGO_ENV=local
python manage.py runserver 0.0.0.0:8001
```

You can set `DJANGO_ENV` to `staging` or `prod` to test local code with staging/production environment variables. Currently, the only environment variable is the location of the static bucket. But soon, we'll have different DBs etc.

### Deploying

Deploying with Zappa is very simple:

* Staging:
    ```
    # RUN THIS COMMAND ONLY IF STATIC FILES HAVE CHANGED
    zappa manage dev "collectstatic --noinput"
    zappa update dev
    ```
    The URL will be staging-lambda.plio.in (To be switched to staging.plio.in once we terminate EB)
* Production:
    ```
    # THIS COMMAND ONLY IF STATIC FILES HAVE CHANGED
    zappa manage prod "collectstatic --noinput"
    zappa update prod
    ```
    The URL will be ivideo.plio.in (TBD)

### Static Files

All our static files are now stored on S3 in the [`plio-static` bucket](https://s3.console.aws.amazon.com/s3/buckets/plio-static?region=ap-south-1&prefix=prod/&showversions=false). Folders inside the bucket:

* `staging`: For staging backend AND local (if we want, we can configure django to use local for local)
* `prod`: For production


## DB Stuff

Great help for all this set up from [this link](https://www.codingforentrepreneurs.com/blog/rds-database-serverless-django-zappa-aws-lambda) for Django/RDS/Zappa and [this link](https://tech.pritamsukumar.com/serverless-zappa/) for some Zappa IAM Details.

**IMPORTANT**: You will need the zappa profile AWS key and Secret Key. Ask Pritam or whoever can give this to you.

DB is hosted on AWS RDS:

* DB Identifier: plio-db
* RDS DB password: d2a12672-7e6a-4488-a365-a0e62adf2659 (UUID4 bases)
* VPC ID: vpc-0a48a661


## ---- OLD NOTES BELOW ----

## Requirements

### Python
* `python 3.7`
* `virtualenv` (usually installed via `pip install virtualenv`)
* A virtual environment created with `python 3.8.5`:
```
virtualenv ~/eb-virt
```

### Postgres

#### Mac
```
brew install postgresql
```

#### Windows
* Download Postgres server from [here](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
* Ensure that the installation includes the PostgreSQL Unicode ODBC driver. (Not required if you selected all options while installing)
* _Note_: Once installed, the PostgreSQL server appears in the `Services` tab in Windows Task Manager.
* Add the PostgreSQL bin directory path to the `PATH` environmental variable
* Confirm the installation by typing `psql` in the Command Prompt

## Starting

I followed the instructions [here](https://www.digitalocean.com/community/tutorials/how-to-use-postgresql-with-your-django-application-on-ubuntu-14-04). It's for Ubuntu, but the commands work perfectly on a Mac. 

* Instead of `myproject`, I used `ivideo_db`, and instead of `myprojectuser`, I used `ivideo_root`. Password is the usual Avanti password. 
* On AWS
```
DB user: ivideoroot
password: USUAL_AVANTI_PASSWORD
```
* Administrator account credentials:
```
username: ivideo_admin
email: avantied@avanti.in
password: USUAL_AVANTI_PASSWORD
```

```
source ~/eb-virt/bin/activate
pip install django psycopg2-binary
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py makemigrations

python3 manage.py collectstatic
python3 manage.py runserver
```

## Troubleshooting

* You can ssh into the instance to figure things out.

```
eb ssh -i INSTANCE_ID
```
The instance ID should be available in the errot message. 
* Migration problems on the EB instance. Solution from [here](https://stackoverflow.com/questions/62457165/deploying-django-to-elastic-beanstalk-migrations-failed/63074781#63074781)


## TODO

[] Implement custom commands from [here](https://realpython.com/deploying-a-django-app-to-aws-elastic-beanstalk/)

## Elastic Beanstalk things

The packages that are nee
### References

1. Digital Ocean's guide to setting up an [empty Django Project with Postgres](https://www.digitalocean.com/community/tutorials/how-to-use-postgresql-with-your-django-application-on-ubuntu-14-04)
2. Decent detailed tutorial series on [Elastic Beanstalk + Django](https://www.starwindsoftware.com/blog/deploying-django-project-to-aws-elastic-beanstalk) and [Postgres](https://www.starwindsoftware.com/blog/deploying-django-project-to-aws-elastic-beanstalk-part-2-database-settings-configuration)
3. [Offical AWS Docs for this combo](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create-deploy-python-django.html)
4. Getting EB CLI to work properly. [Official](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-configuration.html) + [SO help](https://stackoverflow.com/questions/29190202/how-to-change-the-aws-account-using-the-elastic-beanstalk-cli)
5. Crazy. Static file uploading error. [SO Link](https://stackoverflow.com/questions/62273041/aws-elastic-beanstalk-can-not-find-static-files-for-django-app)
