#!/usr/bin/env bash

docker exec -it "${PWD##*/}_backend_1" ./manage.py "${@:1}"
