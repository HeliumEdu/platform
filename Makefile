.PHONY: all env docker-env virtualenv install install-dev nopyc clean build build-migrations migrate test build-docker run-docker publish-docker

SHELL := /usr/bin/env bash
PLATFORM_VENV ?= .venv
AWS_REGION ?= us-east-1
TAG_VERSION ?= latest
PLATFORM ?= linux/amd64

all: env virtualenv install build migrate test build-docker

env:
	cp -n .env.example .env | true

docker-env:
	@if [ ! -f ".env" ]; then \
		cp -n .env.docker.example .env | true; \
		echo "--> Adding local S3 'storage' hostname to /etc/hosts"; \
		sudo sh -c "grep -qxF '127.0.0.1 storage' /etc/hosts || echo '127.0.0.1 storage' >> /etc/hosts"; \
	fi

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
	docker buildx build --target platform_resource -t helium/platform-resource:latest -t helium/platform-resource:$(TAG_VERSION) --platform=$(PLATFORM) .
	docker buildx build -t helium/platform-resource:latest --load .

	docker buildx build --target platform_api -t helium/platform-api:latest -t helium/platform-api:$(TAG_VERSION) --platform=$(PLATFORM) .
	docker buildx build -t helium/platform-api:latest --load .

	docker buildx build --target platform_worker -t helium/platform-worker:latest -t helium/platform-worker:$(TAG_VERSION) --platform=$(PLATFORM) .
	docker buildx build -t helium/platform-worker:latest --load .

run-docker: docker-env
	docker compose up -d

publish-docker:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com

	docker tag helium/platform-resource:$(TAG_VERSION) $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/helium/platform-resource:$(TAG_VERSION)
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/helium/platform-resource:$(TAG_VERSION)

	docker tag helium/platform-api:$(TAG_VERSION) $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/helium/platform-api:$(TAG_VERSION)
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/helium/platform-api:$(TAG_VERSION)

	docker tag helium/platform-worker:$(TAG_VERSION) $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/helium/platform-worker:$(TAG_VERSION)
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.us-east-1.amazonaws.com/helium/platform-worker:$(TAG_VERSION)