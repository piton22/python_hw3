FROM python:3.11

# RUN apt-get update && apt-get install -y postgresql-client

RUN mkdir /fastapi_app

WORKDIR /fastapi_app

COPY .env .  
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN chmod a+x docker/*.sh
