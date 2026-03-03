FROM python:3.9

RUN apt-get update && apt-get -y install git libfontconfig libssl-dev build-essential libffi-dev

RUN pip install poetry

ENV DATA_FOLDER=/data

RUN mkdir -p /data && chmod -R +r /data

WORKDIR /code
COPY pyproject.toml README.md ./

RUN poetry install

COPY ./ .
