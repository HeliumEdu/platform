<p align="center"><img src="https://www.heliumedu.com/assets/img/logo_full_blue.png" /></p>

![Python Versions](https://img.shields.io/badge/python-%203.12%20-blue)
[![Coverage](https://img.shields.io/codecov/c/github/HeliumEdu/platform)](https://codecov.io/gh/HeliumEdu/platform)
[![Build](https://img.shields.io/github/actions/workflow/status/HeliumEdu/platform/build.yml)](https://github.com/HeliumEdu/platform/actions/workflows/build.yml)
[![Code Quality](https://app.codacy.com/project/badge/Grade/0cb1b256044e43739735987214f3a796)](https://app.codacy.com/gh/HeliumEdu/platform/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
![GitHub License](https://img.shields.io/github/license/heliumedu/platform)

# Helium Platform

The backend `platform` for [Helium Edu](https://www.heliumedu.com/), which includes both API and worker functionality. Docs for
integrating with the API can be found [here](https://api.heliumedu.com/docs/).

Released container images are published to [Helium's AWS ECR](https://gallery.ecr.aws/heliumedu/).

## Prerequisites

- Docker
- Python (>= 3.12)
- MySQL (>= 8)
- Redis (>= 5)

## Getting Started

The `platform` is developed using Python and [Django](https://www.djangoproject.com).

This project is configured to work with a [Virtualenv](https://virtualenv.pypa.io/en/stable) within a
[Docker](https://www.docker.com/) container. Once provisioned, development can be done offline, as the container built
for development includes [LocalStack](https://www.localstack.cloud/) to emulate AWS services locally.

## Development

### Docker Setup

To provision the Docker container with the Python/Django `platform` build and all dependencies, execute:

```sh
bin/runserver
```

This builds and starts two containers, one for the API (named `helium_platform_api`), and one for the Worker
(named `helium_platform_worker`). Once running, the `platform` API is available at http://localhost:8000, and the
`platform` Worker is running to execute async and scheduled tasks. The shell of containers can be accessed using their
name, like:

```shell
docker exec -it platform-api-1 /bin/bash
```

Inside the `platform` container, you can run Django commands against the app, like:

```sh
python manage.py migrate
python manage.py createsuperuser
```

A superuser extends a basic user (when you register from [the `frontend` website](http://localhost:3000/register)), but
also has access to [the admin site](http://localhost:8000/admin).

#### Image Architecture

By default, the Docker image will be built for `linux/arm64`. To build a native image on an `x86` architecture
instead, set `PLATFORM=amd64`.

### Project Information

The `platform` is split up into several modules, all contained within this repository.  The base configuration is
defined under `conf`. The applications within this project are:

- auth
- common
- feed
- importexport
- planner

There are also some special environment variables that can be set in development or deployment of the project:

- `ENVIRONMENT`
  - `dev-local` provisions hosts as `localhost`
  - `local` provisions hosts as `localhost` for use outside of Docker (ex. when using Django's `runserver` command) 
  - `prod` provisions hosts to be suffixed with `heliumedu.com`
  - Any other env name provisions a prod-like hostname with `<ENVIRONMENT>.` as the prefix
- `PLATFORM_BEAT_MODE`
  - Set to `True` to start a Beat scheduler (only one should ever be running in the fleet) instead of a Worker when launching from [Celery](https://docs.celeryq.dev/en/stable/getting-started/introduction.html)
- `USE_AWS_SECRETS_MANAGER`
  - Set to `True` to use AWS Secrets Manager before falling back to environment variables
- `USE_NGROK`
  - Set to `True` to have [pyngrok](https://github.com/alexdlaird/pyngrok) open a `ngrok` tunnel and provide a real hostname (only works when `ENVIRONMENT` is not `prod`

These and other environment variables can be configured in the `.env` file. This is also where credentials to
third-party services (for example, AWS services like SES) can be set. Do NOT commit real credentials to third-party
services, even in example files.

Before commits are made, be sure to run tests and check the generated coverage report.

```sh
make test
```

### Frontend

The `frontend` is served from a separate repository and can be found [here](https://github.com/HeliumEdu/frontend#readme).
Using Docker, the `frontend` and `platform` containers can be started alongside each other to almost entirely
emulate a `prod`-like environment locally using [the `deploy` project](https://github.com/HeliumEdu/deploy). For
functionality that still requires Internet-connected external services (ex. emails and text messages), provision
[the `dev-local` Terraform Workspace](https://github.com/HeliumEdu/deploy/tree/main/terraform/environments/dev-local),
which is meant to work alongside local Docker development. 

Note that the `frontend` was previously bundled, rendered, and served as a part of this project, but it was pulled out
into its own project with the with `1.4.0` release. For reference, checkout the `1.3.8` tag or download it [here](https://github.com/HeliumEdu/platform/releases/tag/1.3.8)
to see how this was previously done.

### Documentation

Auto-generated API documentation is accessible via any environment at /docs. Additional documentation can be found
on the [Platform Wiki](https://github.com/HeliumEdu/platform/wiki/Helium-Platform-Documentation).
