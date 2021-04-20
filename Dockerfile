# base image
FROM python:3.8

# where your code lives
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# install dependencies
RUN pip install --upgrade pip
# copy whole project to your docker home directory.
COPY . .
COPY entrypoint.sh .

# run this command to install all dependencies
RUN pip install -r requirements.txt
# port where the Django app runs
EXPOSE ${APP_PORT}

ENTRYPOINT ["/app/entrypoint.sh"]
