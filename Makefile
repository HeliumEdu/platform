.PHONY: all env virtualenv install install-dev nopyc clean build build-migrations migrate test

SHELL := /usr/bin/env bash
PLATFORM_VENV ?= .venv

all: env virtualenv install build migrate test

env:
	cp -n .env.example .env | true

virtualenv:
	@if [ ! -d "$(PLATFORM_VENV)" ]; then \
		python3 -m pip install virtualenv; \
		python3 -m virtualenv $(PLATFORM_VENV); \
	fi

install: env virtualenv
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python -m pip install -r requirements.txt -r requirements-deploy.txt; \
	)

install-dev: env virtualenv
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python -m pip install -r requirements.txt -r requirements-dev.txt; \
	)

nopyc:
	find . -name '*.pyc' | xargs rm -f || true
	find . -name __pycache__ | xargs rm -rf || true

clean: nopyc
	rm -rf build $(PLATFORM_VENV)

build: install
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python manage.py collectstatic --noinput; \
	)

build-migrations: install
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python manage.py makemigrations; \
	)

migrate: install
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python manage.py migrate; \
	)

test: install-dev
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		coverage run manage.py test && coverage report && coverage html && coverage xml; \
	)

build-docker:
	docker build -t helium-platform .
	docker tag helium-platform:latest helium:platform

run-docker: env
	docker compose --env-file .env up -d
