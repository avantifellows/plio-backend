FROM nginx:stable-alpine

RUN mkdir /app
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
WORKDIR /app
