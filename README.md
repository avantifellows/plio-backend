Avanti Interactive Video
========================

## Requirements

### Python
* `python 3.8.5`
* `virtualenv` (usually installed via `pip install virtualenv`)
* A virtual environment created with `python 3.8.5`:
```
virtualenv ~/eb-virt
```

### Postgres

```
brew install postgresql
```

## Starting

I followed the instructions [here](https://www.digitalocean.com/community/tutorials/how-to-use-postgresql-with-your-django-application-on-ubuntu-14-04). It's for Ubuntu, but the commands work perfectly on a Mac. 

* Instead of `myproject`, I used `ivideo_db`, and instead of `myprojectuser`, I used `ivideo_root`. Password is the usual Avanti password. 
* Administrator account credentials:
```
username: ivideo_admin
email: avantied@avanti.in
password: USUAL_AVANTI_PASSWORD
```

```
source ~/eb-virt/bin/activate
```

### References

1. Digital Ocean's guide to setting up an [empty Django Project with Postgres](https://www.digitalocean.com/community/tutorials/how-to-use-postgresql-with-your-django-application-on-ubuntu-14-04)
2. Decent detailed tutorial series on [Elastic Beanstalk + Django + Postgres](https://www.starwindsoftware.com/blog/deploying-django-project-to-aws-elastic-beanstalk)
3. [Offical AWS Docs for this combo](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create-deploy-python-django.html)
4. Getting EB CLI to work properly. [Official](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-configuration.html) + [SO help](https://stackoverflow.com/questions/29190202/how-to-change-the-aws-account-using-the-elastic-beanstalk-cli)
