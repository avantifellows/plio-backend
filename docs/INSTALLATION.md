## Installation


### Pre-requisites
#### Docker
Download docker for your operating system: https://docs.docker.com/get-docker/

### Installation steps
1. Clone the repository and change the working directory
    ```sh
    git clone https://github.com/avantifellows/plio-backend.git
    cd plio-backend
    ```
2. For **DEVELOPMENT PURPOSE** only, make sure Docker Desktop application is running and docker version is giving a proper output.
    ```sh
    docker --version
    ```
3. Set up your `.env` file by copying `.env.example` file
    ```sh
    cp .env.example .env
    ```
4. Update environment variables in your `.env` file based on your environment. For all available settings, see our [Environment variables guide](ENV.md).
5. Build the docker image and run the containers using just one command:
    ```sh
    docker-compose up -d --build
    ```
6. For **DEVELOPMENT PURPOSE** only, run the following command to install pre-commit
    ```sh
    pre-commit install
    ```
7. Set up either [OTP functionality](ONE-TIME-PIN.md) or [Google sign-in](oauth/GOOGLE-OAUTH2.md) for users to be able to log in.
8. Your backend API should be accessible at http://0.0.0.0:8001/api/v1 and the Django Admin dashboard will be accessible at http://0.0.0.0:8001/admin


### Additional steps
1. To enable OTP support, visit [One Time Pin guide](ONE-TIME-PIN.md).
2. To enable Google sign-in support, visit [Google OAuth2 guide](oauth/GOOGLE-OAUTH2.md).
