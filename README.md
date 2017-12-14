[![Build Status](https://travis-ci.org/HeliumEdu/platform.svg?branch=master)](https://travis-ci.org/HeliumEdu/platform)

# Helium Platform Project

## Prerequisites
* Python (>= 2.7, >= 3.6)
* Pip (>= 9.0)
* MySQL (>= 5.7)
* Redis (>= 3.2)

## Virtualenv
Virtualenv creates isolated Python development environments so your development environment(s play
nicely with each other in regards to dependencies, permissions, and a myriad of other ways. While this is not necessary for development, it
is highly recommended.
 
This project is configured to expect a Virtualenv in the `.venv` folder, and it can be setup like this:

```
pip install virtualenv
virtualenv .venv
```

If you're unfamiliar with how works, [read up on it](https://virtualenv.pypa.io/en/stable/). The short version is, you only need to run the
above one time. After that point, you only need to execute the following command to active and use the isolated environment when developing:

```
source .venv/bin/activate
```

## Getting Started
The Platform is developed on [Django](https://www.djangoproject.com/). To setup the Python/Django Platform build environment, execute:

```
make install
```

To ensure the database is in sync with the latest schema, database migrations are generated and run with Django. To run migrations, execute:

```
make migrate
```

Once migrations have been run, you can create a super user, which is a standard user that also has access to the /admin site.

```
python manage.py createsuperuser
```

Before commits are made, be sure to run tests and check the generated coverage report

```
make test
```

### Fixtures
Fixtures are an easy way to load data from a JSON blob into a database, as we just did above. However, these should never be loaded into
non-dev environments. 

## Development
### Modules
The Platform project is split up into several modules, all contained within this repository.They are independent modules that can be deployed
separately, functioning on separate nodes for scalability, as needed.

The project's base configuration is defined under `conf`. Application-specific configuration variables should have their application name as their
prefix.

* users
* feed
* planner

### Vagrant Development
To emulate a prod-like environment, use the Vagrant box. It's setup is described more thoroughly in the [deploy](https://github.com/HeliumEdu/deploy)
project. This is the recommended way to develop and test for production as this environment is provisioned in the same way other prod-like
environments are deployed and interacts with related projects as necessary.

As the Vagrant environment does take a bit more time to setup (even though the setup is largely automated) and can consume more developer
and system resources, the local development environment described below is the quickest and easiest way to get up and running.

### Local Development
This is the simplest way to get started with minimal effort, as it requires no additional projects or environments. To get going (assuming
you have followed the "Getting Started" directions above), you should have the ENVIRONMENT environment variable set to "dev". Then, simply
move the example config into place with `cp -n .env.example .env`.

Now you're all set! To start the development server, execute:

```
python manage.py runserver
```

A development server will be started at http://localhost:8000.

Note that credentials to third-party services (for example, AWS services like SES) need to be set in the `.env` file
before those services will work properly. Do NOT commit real credentials to third-party services, even in example files.