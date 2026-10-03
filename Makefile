SHELL := /bin/bash
COMPOSE_DEMO := docker compose --env-file .env -f docker-compose.yml -f docker-compose.demo.yml
COMPOSE_PROD := docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml

.PHONY: dev check test build docker-config docker-build docker-up docker-down migrate seed-demo smoke logs backup-postgres

dev:
	@echo "Run backend and frontend in separate terminals; see README Development."

check:
	cd frontend && npm run lint && npm run typecheck
	cd backend && .venv/bin/python -m compileall -q app

test:
	cd frontend && npm test
	cd backend && .venv/bin/pytest -q

build:
	cd frontend && npm run build

docker-config:
	$(COMPOSE_DEMO) config >/dev/null

docker-build:
	$(COMPOSE_DEMO) build backend frontend

docker-up:
	$(COMPOSE_DEMO) up -d --build

docker-down:
	$(COMPOSE_DEMO) down

migrate:
	$(COMPOSE_DEMO) run --rm migrate

seed-demo:
	$(COMPOSE_DEMO) --profile demo-seed run --rm seed-demo

smoke:
	DEMO_MODE=true ./scripts/smoke-test.sh http://localhost:$${PUBLIC_HTTP_PORT:-80}

logs:
	$(COMPOSE_DEMO) logs -f --tail=200 reverse-proxy frontend backend migrate

backup-postgres:
	@mkdir -p backups
	$(COMPOSE_DEMO) exec -T postgres pg_dump -U $${POSTGRES_USER:-fingraph_qris} -d $${POSTGRES_DB:-fingraph_qris} -Fc > backups/fingraph-qris-$$(date +%Y%m%d-%H%M%S).dump
