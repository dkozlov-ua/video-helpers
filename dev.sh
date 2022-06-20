#!/usr/bin/env bash

ACTION=$1

if   [[ $ACTION == "makemigrations" ]]; then
     docker build --tag moviemaker:latest . \
  && docker-compose --env-file env.dev run --rm --entrypoint "./manage.py makemigrations" backend
elif [[ $ACTION == "migrate" ]]; then
     docker build --tag moviemaker:latest . \
  && docker-compose --env-file env.dev run --rm --entrypoint "./manage.py migrate" backend
elif [[ $ACTION == "start" ]]; then
     docker build --tag moviemaker:latest . \
  && docker-compose --env-file env.dev up --remove-orphans --detach \
  && docker-compose --env-file env.dev logs --tail 100 --follow
elif [[ $ACTION == "stop" ]]; then
     docker-compose --env-file env.dev down --remove-orphans
else
  exit 2
fi
