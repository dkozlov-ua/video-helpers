#!/usr/bin/env bash

   python manage.py collectstatic --noinput --link \
&& python manage.py migrate --noinput \
&& gunicorn backend.wsgi "${@:1}"
