FROM ubuntu/apache2

RUN apt update
RUN apt install -y python-is-python3 python3-pip python3-virtualenv python3-setuptools
RUN apt install -y libapache2-mod-wsgi-py3 python3-mysqldb pkg-config default-libmysqlclient-dev
RUN apt install -y libjpeg-dev zlib1g-dev
RUN apt install -y supervisor

RUN apt install -y npm
RUN npm install yuglify -g

RUN mkdir -p /var/log/helium /var/log/supervisor
RUN mkdir /usr/local/venvs

COPY heliumedu.apache.conf /etc/apache2/sites-enabled/000-default.conf

WORKDIR /app

COPY conf conf
COPY helium helium
COPY manage.py .
COPY requirements.txt .
COPY requirements-deploy.txt .

RUN virtualenv /usr/local/venvs/platform
RUN /usr/local/venvs/platform/bin/python -m pip install -r requirements.txt -r requirements-deploy.txt

RUN ln -sf /dev/stdout /var/log/apache2/access.log
RUN ln -sf /dev/stderr /var/log/apache2/error.log

#RUN ln -sf /dev/stdout /var/log/helium/django.log
#RUN ln -sf /dev/stdout /var/log/helium/health_check.log
#RUN ln -sf /dev/stdout /var/log/helium/platform.log

RUN ln -sf /dev/stdout /var/log/supervisor/celerybeat.log
RUN ln -sf /dev/stdout /var/log/supervisor/celeryworker_1.log
RUN ln -sf /dev/stdout /var/log/supervisor/celeryworker_2.log

RUN chown www-data:www-data -R /var/log/helium

EXPOSE 80

CMD ["apache2ctl", "-D", "FOREGROUND"]
