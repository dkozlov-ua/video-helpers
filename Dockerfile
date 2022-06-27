FROM python:3

RUN    apt-get update \
    && apt-get install -y \
         ffmpeg

WORKDIR /usr/src/app

# install python modules
RUN pip3 install --no-cache-dir -U pipenv
COPY Pipfile.lock .
RUN    pipenv requirements > /tmp/requirements.txt \
    && pip3 install --no-cache-dir -U -r /tmp/requirements.txt

# copy application files
COPY . .
ENV DJANGO_SETTINGS_MODULE=backend.settings
