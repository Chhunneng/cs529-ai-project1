.PHONY: up dev dev-build down logs ps build restart migrate backend-shell worker-shell

COMPOSE_DEV := docker compose -f docker-compose.yml -f docker-compose.dev.yml

up:
	docker compose up -d --build

# Live reload: bind-mounts source; uvicorn --reload, watchfiles worker, next dev.
# Use `make dev-build` after Dockerfile or dependency (lockfile) changes.
dev:
	$(COMPOSE_DEV) up

dev-build:
	$(COMPOSE_DEV) up --build

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=200

build:
	docker compose build

restart:
	docker compose restart

migrate:
	$(COMPOSE_DEV) run --rm backend alembic upgrade head

backend-shell:
	$(COMPOSE_DEV) run --rm backend bash

worker-shell:
	$(COMPOSE_DEV) run --rm worker bash
