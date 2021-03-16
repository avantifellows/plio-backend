## Deployment
This document covers steps on setting up this repository on various cloud hosting providers.

  - [AWS](#aws)

### AWS

Plio utilizes [zappa](https://github.com/zappa/Zappa) to deploy to AWS Lambda. Set up Zappa before starting on the deployment as it requires Zappa credentials.

Deploying with Zappa is very simple:

#### Staging
```sh
# RUN THIS COMMAND ONLY IF STATIC FILES HAVE CHANGED
zappa manage dev "collectstatic --noinput"
zappa update dev
```

#### Production
```sh
# THIS COMMAND ONLY IF STATIC FILES HAVE CHANGED
zappa manage prod "collectstatic --noinput"
zappa update prod
```
