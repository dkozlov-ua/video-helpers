FROM python:3

RUN    apt-get update \
    && apt-get install -y \
         ffmpeg

WORKDIR /usr/src/app

# install python modules
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -U -r /tmp/requirements.txt

# copy application files
COPY . .
ENV DJANGO_SETTINGS_MODULE=backend.settings
