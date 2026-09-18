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

load-data:
	docker compose exec -T web python manage.py import_stations || true
	docker compose exec -T web python manage.py load_stations || true
	docker compose exec -T web python manage.py geocode_stations || true

test:
	docker compose exec -T web pytest

lint:
	docker compose exec -T web ruff check .
	docker compose exec -T web mypy .

shell:
	docker compose exec web python manage.py shell
