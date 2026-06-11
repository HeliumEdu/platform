<p align="center">
  <img src="https://raw.githubusercontent.com/HeliumEdu/www/main/src/assets/img/helium-logo.png" alt="Helium" width="300" />
  <br />
  <img src="https://raw.githubusercontent.com/HeliumEdu/www/main/src/assets/img/og-default.png" alt="Helium - Student Planner" width="800" />
</p>

---

[**Helium**](https://www.heliumedu.com) is a free, color-coded online student planner for classes, homework, grades, and notes.

<p align="center">
  <a href="https://apps.apple.com/us/app/helium-student-planner/id6758323154"><img src="https://raw.githubusercontent.com/HeliumEdu/www/main/src/assets/img/ios-badge.png" alt="Download on the App Store" height="50" /></a>
  &nbsp;
  <a href="https://play.google.com/store/apps/details?id=com.heliumedu.heliumapp"><img src="https://raw.githubusercontent.com/HeliumEdu/www/main/src/assets/img/play-badge.png" alt="Get it on Google Play" height="50" /></a>
</p>

<p align="center">
  <a href="https://www.patreon.com/alexdlaird/membership"><img src="https://raw.githubusercontent.com/HeliumEdu/www/main/public/img/support-patreon.svg" alt="Support on Patreon" height="30" /></a>
</p>

---

# Helium Platform

[![Coverage](https://img.shields.io/codecov/c/github/HeliumEdu/platform)](https://codecov.io/gh/HeliumEdu/platform)
[![Build](https://img.shields.io/github/actions/workflow/status/HeliumEdu/platform/build.yml)](https://github.com/HeliumEdu/platform/actions/workflows/build.yml)
[![Code Quality](https://app.codacy.com/project/badge/Grade/0cb1b256044e43739735987214f3a796)](https://app.codacy.com/gh/HeliumEdu/platform/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
![GitHub License](https://img.shields.io/github/license/heliumedu/platform)

The backend `platform` for Helium - Student Planner, including API and worker functionality. Docs for
integrating with the API can be found [here](https://api.heliumedu.com/docs/).

Released container images are published to [Helium's AWS ECR](https://gallery.ecr.aws/heliumedu/).

## Prerequisites

- Docker
- Python (>= 3.12)
- MySQL (>= 8)
- Redis (>= 7)

## Getting Started

The `platform` is developed using Python and [Django](https://www.djangoproject.com).

This project is configured to work with a [Virtualenv](https://virtualenv.pypa.io/en/stable) within a
[Docker](https://www.docker.com/) container. Once provisioned, development can be done offline, as the container built
for development includes [LocalStack](https://www.localstack.cloud/) to emulate AWS services locally.

## Development

### Docker Setup

To provision the Docker container with the Python/Django `platform` build and all dependencies, execute:

```sh
make
```

This builds and starts two containers, one for the API (named `platform-api-1`), and one for the Worker
(named `platform-worker-1`). Once running, the `platform` API is available at http://localhost:8000, and the
`platform` Worker is running to execute async and scheduled tasks.

To create an admin user, you can run:

```sh
docker exec -it platform-api-1 python manage.py createsuperuser
```

An admin extends a basic user (when you register from [the `frontend` website](http://localhost:8080/signup)) with
access to [the admin site](http://localhost:8000/admin).

The shell of containers can be accessed using their name, like:

```shell
docker exec -it platform-api-1 /bin/bash
```

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
  - `local` provisions hosts as `localhost` for use outside of Docker (e.g. when using Django's `runserver` command) 
  - `prod` provisions hosts to be suffixed with `heliumedu.com`
  - Any other env name provisions a prod-like hostname with `<ENVIRONMENT>.` as the prefix
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
The `frontend` and `platform` containers can be started alongside each other to almost entirely
emulate a `prod`-like environment locally. For functionality that still requires Internet-connected external
services (e.g. emails and text messages), provision [the `dev-local` Terraform Workspace](https://github.com/HeliumEdu/infra/tree/main/terraform/environments/dev-local),
which is meant to work alongside local Docker development.

### Documentation

Auto-generated API documentation is accessible via any environment at /docs.
