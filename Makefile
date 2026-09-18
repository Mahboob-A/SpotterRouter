.PHONY: build up down logs migrate load-data test lint shell

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f web

migrate:
	docker compose exec -T web python manage.py migrate

STATIONS_CSV ?= fuel-prices-for-be-assessment.csv
LOAD_STATIONS_FLAGS ?=

load-data:
	docker compose exec -T web python manage.py import_stations $(STATIONS_CSV)
	docker compose exec -T web python manage.py load_stations $(LOAD_STATIONS_FLAGS)
	docker compose exec -T web python manage.py geocode_stations


test:
	docker compose exec -T web pytest

lint:
	docker compose exec -T web ruff check .
	docker compose exec -T web mypy .

shell:
	docker compose exec web python manage.py shell
