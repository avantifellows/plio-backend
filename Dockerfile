# base image
FROM python:3.8
# setup environment variable
ENV DOCKERHOME=/projects/plio/backend

# set work directory
RUN mkdir -p $DOCKERHOME

# where your code lives
WORKDIR $DOCKERHOME

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# install dependencies
RUN pip install --upgrade pip
# copy whole project to your docker home directory.
COPY . $DOCKERHOME
COPY entrypoint.sh $DOCKERHOME/
RUN chmod +x entrypoint.sh
# run this command to install all dependencies
RUN pip install -r requirements.txt
# # port where the Django app runs
# EXPOSE 8000
# start server
# CMD python manage.py runserver

ENTRYPOINT ["/projects/plio/backend/entrypoint.sh"]
