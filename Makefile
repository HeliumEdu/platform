.PHONY: all build build-migrations clean

build:
	cp .env.example .env
	pip install -r requirements.txt --user
	python manage.py collectstatic --noinput

build-migrations:
	python manage.py makemigrations users planner

migrate:
	python manage.py migrate

test:
	python manage.py test
