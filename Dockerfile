FROM ubuntu/apache2

RUN apt update
RUN apt install -y python-is-python3 python3-pip python3-virtualenv python3-setuptools
RUN apt install -y libapache2-mod-wsgi-py3 python3-mysqldb pkg-config default-libmysqlclient-dev
RUN apt install -y libjpeg-dev zlib1g-dev
RUN apt install -y supervisor

RUN apt install -y npm
RUN npm install yuglify -g

RUN mkdir -p /usr/local/venvs
RUN chown -R www-data:www-data /usr/local/venvs

USER www-data

COPY container/supervisord.conf /etc/supervisor
COPY container/apache-site.conf /etc/apache2/sites-enabled/000-default.conf
COPY container/apache-envvars /etc/apache2/envvars
COPY container/celerybeat.conf /etc/supervisor/conf.d
COPY container/celeryworker.conf /etc/supervisor/conf.d
COPY container/docker-entrypoint.sh /usr/local/bin

WORKDIR /app

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

EXPOSE 80

USER root

RUN touch celerybeat-schedule.db
RUN chown ubuntu:ubuntu celerybeat-schedule.db

CMD ["sh", "/usr/local/bin/docker-entrypoint.sh"]

