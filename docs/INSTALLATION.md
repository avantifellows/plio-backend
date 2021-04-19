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
2. Make sure Docker is installed and docker version is running fine.
    ```sh
    docker --version
    ```
3. Build the image and run the containers using just one command:
    #### Development
    ```sh
    pip install -r requirements-dev.txt
    ```

    #### Production
    ```sh
    pip install -r requirements.txt
    ```

    In case of errors in macOS venv, run the following commands to configure OpenSSL properly:
    ```sh
    export LDFLAGS="-L/usr/local/opt/openssl/lib"
    export CPPFLAGS="-I/usr/local/opt/openssl/include"
    ```
4. Set up your `.env` file by copying `.env.example` file
    ```sh
    cp .env.example .env
    ```
5. Update environment variables in your `.env` file based on your environment. For all available settings, see our [Environment variables guide](ENV.md).
6. For **DEVELOPMENT PURPOSE** only, run the following command to install pre-commit
    ```sh
    pre-commit install
    ```
7. Set up either [OTP functionality](ONE-TIME-PIN.md) or [Google sign-in](oauth/GOOGLE-OAUTH2.md) for users to be able to log in.
8. Your backend API should be accessible at http://0.0.0.0:8001/api/v1 and the Django Admin dashboard will be accessible at http://0.0.0.0:8001/admin


### Additional steps
1. To enable OTP support, visit [One Time Pin guide](ONE-TIME-PIN.md).
2. To enable Google sign-in support, visit [Google OAuth2 guide](oauth/GOOGLE-OAUTH2.md).
