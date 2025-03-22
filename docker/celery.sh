#!/bin/bash

cd /fastapi_app

if [[ "${1}" == "celery" ]]; then
  celery -A src.tasks.celery_app:celery worker -l INFO
elif [[ "${1}" == "flower" ]]; then
  celery -A src.tasks.celery_app:celery flower
fi