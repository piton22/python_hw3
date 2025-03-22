#!/bin/bash

# rm -rf alembic/versions/*
# alembic revision --autogenerate -m "init_tables"
alembic upgrade head

cd src

gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000