.PHONY: all build clean

build:
	pip install -r reqs.txt --user
	python manage.py collectstatic --noinput
	python manage.py makemigrations users planner

migrate:
	python manage.py migrate

test:
	python manage.py test
