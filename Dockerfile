FROM ubuntu:22.04 AS build

RUN apt-get update
RUN apt-get install -y git python3-virtualenv python3-pip python3-setuptools pkg-config default-libmysqlclient-dev

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/venv/bin:$PATH"

WORKDIR /app

COPY requirements.txt .
COPY requirements-deploy.txt .

RUN python3 -m virtualenv /venv
RUN python -m pip install --no-cache-dir -r requirements.txt -r requirements-deploy.txt

######################################################################

FROM ubuntu:22.04 AS platform_api

RUN apt-get update
RUN apt-get install -y --no-install-recommends apache2 libapache2-mod-wsgi-py3 python3-mysqldb libjpeg-dev ca-certificates

RUN groupadd ubuntu
RUN useradd -rm -s /bin/bash -g ubuntu -G sudo -u 1001 ubuntu

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/venv/bin:$PATH"
ENV APACHE_RUN_USER=ubuntu

WORKDIR /app

COPY container/apache2.conf /etc/apache2
COPY container/apache-000-default.conf /etc/apache2/sites-enabled/000-default.conf
COPY container/apache-ports.conf /etc/apache2/ports.conf
COPY container/apache-mod-servername.conf /etc/apache2/mods-enabled/servername.conf

RUN chown -R ubuntu:ubuntu .

COPY --chown=ubuntu:ubuntu conf conf
COPY --chown=ubuntu:ubuntu helium helium
COPY --chown=ubuntu:ubuntu manage.py .
COPY --from=build --chown=ubuntu:ubuntu /venv /venv

EXPOSE 8000

CMD ["apache2ctl", "-D", "FOREGROUND"]

######################################################################

FROM ubuntu:22.04 AS platform_worker

RUN apt-get update
RUN apt-get install -y --no-install-recommends supervisor python3-mysqldb libjpeg-dev ca-certificates

RUN groupadd ubuntu
RUN useradd -rm -s /bin/bash -g ubuntu -G sudo -u 1001 ubuntu

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/venv/bin:$PATH"

WORKDIR /app

COPY container/supervisord.conf /etc/supervisor/
COPY container/supervisor-celeryworker.conf /etc/supervisor/conf.d/celeryworker.conf
COPY container/supervisor-celerybeat.conf /etc/supervisor/conf.d/celerybeat.conf.disabled
COPY container/docker-worker-entrypoint.sh /docker-entrypoint.sh

RUN chown -R ubuntu:ubuntu .

COPY --chown=ubuntu:ubuntu conf conf
COPY --chown=ubuntu:ubuntu helium helium
COPY --chown=ubuntu:ubuntu manage.py .
COPY --from=build --chown=ubuntu:ubuntu /venv /venv

ENTRYPOINT ["/docker-entrypoint.sh"]
