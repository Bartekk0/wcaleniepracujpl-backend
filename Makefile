.PHONY: up down logs build lint test

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

lint:
	ruff check .

test:
	pytest -q
