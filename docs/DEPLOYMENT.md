## Deployment
This document covers steps on setting up this repository on various cloud hosting providers.

  - [Pre-requisites](#pre-requisites)
  - [AWS](#aws)

### Pre-requisites
1. Set up your `zappa_settings.json` file by copying `zappa_settings.example.json` file
    ```sh
    cp zappa_settings.example.json zappa_settings.json
    ```
2. Update environment variables in your `zappa_settings.json` file based on your environment. For all available settings, see our [Zappa Settings guide](ZAPPA-SETTINGS.md).

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
