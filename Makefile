.PHONY: all env install build build-migrations migrate test

all: env install build migrate test

env:
	cp -n .env.example .env | true

install: env
	python -m pip install -r requirements.txt --user

build:
	python manage.py collectstatic --noinput

build-migrations: env install
	python manage.py makemigrations

migrate:
	python manage.py migrate

test:
	python -m coverage run manage.py test && python -m coverage html
