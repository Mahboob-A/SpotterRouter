.PHONY: build up down logs migrate load-data test lint shell

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f backend

migrate:
	docker compose exec -T backend python manage.py migrate

STATIONS_CSV ?= fuel-prices-for-be-assessment.csv
LOAD_STATIONS_FLAGS ?=

load-data:
	docker compose exec -T backend python manage.py import_stations $(STATIONS_CSV)
	docker compose exec -T backend python manage.py load_stations $(LOAD_STATIONS_FLAGS)
	docker compose exec -T backend python manage.py geocode_stations

test:
	docker compose exec -T backend pytest

lint:
	docker compose exec -T backend ruff check .
	docker compose exec -T backend mypy .

shell:
	docker compose exec backend python manage.py shell
