# Platform Project

## Prerequisites
* Python (>= 2.7)
* Pip (>= 9.0)
* MySQL (>= 5.7)
* Redis (>= 3.2)

## Getting Started
The Platform is developed on [Django](https://www.djangoproject.com/). To run the Python/Django Platform build, execute:

```
make build
```

To ensure the database is in sync with the latest schema, database migrations are generated and run with Django. To run migrations, execute:

```
make migrate
```

Once migrations have been run, you can create an admin user.

```
python manage.py createsuperuser
```

Before commits are made, be sure to run tests. Tests can be run using the first command below, and code coverage can be analyzed using the second,
assuming `coverage` is installed (install with `pip install coverage`).
 
```
python manage.py test
coverage run --source='.' manage.py test && coverage report
```

### Fixtures
Fixtures are an easy way to load data from a JSON blob into a database, as we just did with vendor data. However, these should never be loaded into
production.

### Superusers
Superusers may not always fully function properly, as they are created through a mechanism handled by Django rather than through the impelemented
registration flow. As a result, they should not be relied on, and only one should ever be created—this gives you access to the Django admin for the
first time. From this point forward, users should be created through the proper registration flow, and if those users are to be administrators,
their user permissions should be elevated properly through the admin. 

## Development
Once the project has been built and migrations applied, the Platform can be started in a few different ways. For quick and easy local development,
see the "Local Development" section below, which uses in-memory databases and a dev server for easy debugging.

To emulate a production environment, use the Vagrant box, available in the `server-configuration` project. This is the recommended way to develop
and test the Platform, as it is quick and easy to setup, and it fully emulates a production environment—the Vagrant environment is provisioned in
the same way staging and production environments are deployed, using Ansible scripts.

### Modules
The Platform project is split up into several modules, all contained within this repository. Eventually, they should be made into Pip dependencies
(which would also allow the Crawler project to make use of a more modular import of necessary Platform components), but they are currently simply
included as sub-applications in Django. Still, they are independent modules that can be deployed separately, functioning on separate nodes for
scalability, as needed.

The project's base configuration is defined under `conf`. Application-specific configuration variables should have their application name as their
prefix.

* users

### Local Development
Development can be done locally without the use of provisioning through Ansible scripts. To develop in this way, you should have the ENVIRONMENT
variable set to "dev" for configs to pickup and use the locally committed .env file.

Then, to start the development server, simply execute:

```
python manage.py runserver
```

Django will start a development server at http://localhost:8000.