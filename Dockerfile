FROM ubuntu:22.04

RUN apt-get update
RUN apt-get install -y git python-is-python3 python3-pip python3-virtualenv python3-setuptools python3-mysqldb  \
    pkg-config default-libmysqlclient-dev libjpeg-dev zlib1g-dev

RUN groupadd ubuntu
RUN useradd -rm -s /bin/bash -g ubuntu -G sudo -u 1001 ubuntu

RUN mkdir -p /usr/local/venvs
RUN chown -R ubuntu /usr/local/venvs

WORKDIR /app

RUN chown -R ubuntu:ubuntu .

COPY conf conf
COPY helium helium
COPY manage.py .

ENV PYTHONUNBUFFERED=1
ENV PLATFORM_VENV=/usr/local/venvs/platform

RUN virtualenv $PLATFORM_VENV
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    --mount=type=bind,source=requirements-deploy.txt,target=requirements-deploy.txt \
    $PLATFORM_VENV/bin/python -m pip install -r requirements.txt -r requirements-deploy.txt
