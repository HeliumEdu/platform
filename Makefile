.PHONY: all env install build build-migrations migrate test test-coverage

all: env install build migrate test

env:
	cp -n .env.example .env | true

install:
	pip install -r requirements.txt

build: env install
	python manage.py collectstatic --noinput

build-migrations: env install
	python manage.py makemigrations

migrate: env install
	python manage.py migrate

test: env install
	python manage.py test

test-coverage: env install
	coverage run --source='.' manage.py test && coverage report
