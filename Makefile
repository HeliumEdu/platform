.PHONY: all env docker-env venv install install-dev nopyc clean build-dev build-migrations migrate-dev test run-devserver build-docker run-docker stop-docker restart-docker publish-docker

SHELL := /usr/bin/env bash
PYTHON_BIN := python
PLATFORM_VENV ?= venv
TAG_VERSION ?= latest
PLATFORM ?= arm64

all: test build-docker run-docker

env:
	cp -n .env.example .env | true

docker-env:
	@if [ ! -f ".env" ]; then \
		cp -n .env.docker.example .env | true; \
		echo "--> Adding local S3 'storage' hostname to /etc/hosts"; \
		sudo sh -c "grep -qxF '127.0.0.1 storage' /etc/hosts || echo '127.0.0.1 storage' >> /etc/hosts"; \
	fi

venv:
	$(PYTHON_BIN) -m pip install virtualenv
	$(PYTHON_BIN) -m virtualenv $(PLATFORM_VENV)

install: venv
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python -m pip install -r requirements.txt -r requirements-deploy.txt; \
	)

install-dev: env venv
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		python -m pip install -r requirements.txt -r requirements-dev.txt; \
	)

nopyc:
	find . -name '*.pyc' | xargs rm -f || true
	find . -name __pycache__ | xargs rm -rf || true

clean: nopyc
	rm -rf build $(PLATFORM_VENV)

build-dev: install-dev
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		ENVIRONMENT=local python manage.py collectstatic --noinput; \
	)

build-migrations: install-dev
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		ENVIRONMENT=local python manage.py makemigrations; \
	)

migrate-dev: install-dev
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		ENVIRONMENT=local python manage.py migrate; \
	)

test: install-dev
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		coverage run -m pytest && coverage report && coverage html && coverage xml; \
	)

run-devserver: build-dev migrate-dev
	# This will start a local dev server, outside of Docker. This can be useful during active development, so images
	# don't need to be rebuilt to validate each change.
	@( \
		source $(PLATFORM_VENV)/bin/activate; \
		ENVIRONMENT=local python manage.py runserver; \
	)

build-docker:
	docker buildx build --target platform_resource -t helium/platform-resource:$(PLATFORM)-latest -t helium/platform-resource:$(PLATFORM)-$(TAG_VERSION) --platform=linux/$(PLATFORM) --load .

	docker buildx build --target platform_api -t helium/platform-api:$(PLATFORM)-latest -t helium/platform-api:$(PLATFORM)-$(TAG_VERSION) --platform=linux/$(PLATFORM) --load .

	docker buildx build --target platform_worker -t helium/platform-worker:$(PLATFORM)-latest -t helium/platform-worker:$(PLATFORM)-$(TAG_VERSION) --platform=linux/$(PLATFORM) --load .

run-docker: docker-env
	docker compose up -d

stop-docker: docker-env
	docker compose stop

restart-docker: stop-docker run-docker

publish-docker: build-docker
	aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/heliumedu

	docker tag helium/platform-resource:$(PLATFORM)-$(TAG_VERSION) public.ecr.aws/heliumedu/helium/platform-resource:$(PLATFORM)-$(TAG_VERSION)
	docker push public.ecr.aws/heliumedu/helium/platform-resource:$(PLATFORM)-$(TAG_VERSION)

	docker tag helium/platform-api:$(PLATFORM)-$(TAG_VERSION) public.ecr.aws/heliumedu/helium/platform-api:$(PLATFORM)-$(TAG_VERSION)
	docker push public.ecr.aws/heliumedu/helium/platform-api:$(PLATFORM)-$(TAG_VERSION)

	docker tag helium/platform-worker:$(PLATFORM)-$(TAG_VERSION) public.ecr.aws/heliumedu/helium/platform-worker:$(PLATFORM)-$(TAG_VERSION)
	docker push public.ecr.aws/heliumedu/helium/platform-worker:$(PLATFORM)-$(TAG_VERSION)