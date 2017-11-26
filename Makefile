.PHONY: all build build-migrations clean

_env:
	cp -n .env.example .env | true

build: _env
	pip install -r requirements.txt --user
	python manage.py collectstatic --noinput

build-migrations: _env
	python manage.py makemigrations users planner

migrate: _env
	python manage.py migrate

test: _env
	python manage.py test
