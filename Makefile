.PHONY: all env virtualenv install build build-migrations migrate test

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
		python -m pip install -r requirements.txt; \
	)

build: virtualenv
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python manage.py collectstatic --noinput; \
	)

build-migrations: env virtualenv install
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python manage.py makemigrations; \
	)

migrate: virtualenv
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python manage.py migrate; \
	)

test: virtualenv
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python -m coverage run --source='.' manage.py test && python -m coverage html; \
	)
