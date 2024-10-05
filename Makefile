.PHONY: all env docker-env virtualenv install install-dev nopyc clean build build-migrations migrate test build-docker run-docker

SHELL := /usr/bin/env bash
PLATFORM_VENV ?= .venv
AWS_REGION ?= us-east-1
TAG_VERSION ?= latest

all: env virtualenv install build migrate test

env:
	cp -n .env.example .env | true

docker-env:
	cp -n .env.docker.example .env | true

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
	docker build -t helium/platform .
	docker tag helium/platform:$(TAG_VERSION) helium/platform

	docker build -f Dockerfile-api -t helium/platform-api .
	docker tag helium/platform-api:$(TAG_VERSION) helium/platform-api

	docker build -f Dockerfile-worker -t helium/platform-worker .
	docker tag helium/platform-worker:$(TAG_VERSION) helium/platform-worker

run-docker: docker-env
	docker compose up -d

push-docker:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com

	docker tag helium/platform-api:$(TAG_VERSION) $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/helium/platform-api:$(TAG_VERSION)
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/helium/platform-api:$(AWS_ACCOUNT_ID)

	docker tag helium/platform-worker:$(TAG_VERSION) $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/helium/platform-worker:$(TAG_VERSION)
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/helium/platform-worker:$(AWS_ACCOUNT_ID)