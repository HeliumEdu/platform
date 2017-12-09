.PHONY: all env install build build-migrations migrate test test-coverage

all: install build migrate test

env:
	cp -n .env.example .env | true

install: env
	pip install -r requirements.txt --user

build:
	python manage.py collectstatic --noinput

build-migrations: env install
	python manage.py makemigrations

migrate:
	python manage.py migrate

test:
	python manage.py test

test-coverage:
	coverage run --source='.' manage.py test && coverage report
