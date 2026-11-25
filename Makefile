# Linux / WSL / CI shortcuts. Windows users: see scripts/dev.ps1 (same targets).
.DEFAULT_GOAL := help
SHELL := /bin/bash
NS ?= devsecops360-dev

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

env: ## Create .env with random secrets (first run only)
	@test -f .env || bash scripts/init-env.sh

up: env ## Start core app (db, backend, frontend) ~600 MB
	docker compose up -d --build --wait

up-full: env ## Core app + Prometheus/Grafana/Loki/Alertmanager ~1.3 GB
	docker compose --profile monitoring up -d --build --wait

down: ## Stop everything (keeps data volumes)
	docker compose --profile monitoring --profile loadtest down

nuke: ## Stop and DELETE all data volumes
	docker compose --profile monitoring --profile loadtest down -v

logs: ## Tail backend logs
	docker compose logs -f backend

test: ## Backend unit+integration tests (SQLite) and frontend tests
	pytest
	cd apps/frontend && npm test

test-pg: ## Backend tests against the running Compose Postgres
	TEST_DATABASE_URL=postgresql+psycopg://$$(grep ^POSTGRES_USER .env|cut -d= -f2):$$(grep ^POSTGRES_PASSWORD .env|cut -d= -f2)@localhost:5432/test pytest

lint: ## All linters
	cd apps/backend && ruff check . && bandit -q -r app -c pyproject.toml
	cd apps/frontend && npm run lint && npm run typecheck
	yamllint -c .yamllint.yml .

smoke: ## Smoke tests against http://localhost:8080
	SMOKE_BASE_URL=http://localhost:8080 pytest tests/smoke -v

e2e: ## Playwright E2E against http://localhost:8080
	cd tests/e2e && npm ci && npx playwright test

load: ## Locust baseline (25 users, 3 min)
	bash load-testing/run.sh baseline

scan: ## Local security scans (needs Docker)
	bash scripts/security-scan.sh

backup: ## Back up the Compose database
	bash scripts/backup/backup.sh

restore-verify: ## Restore latest backup into a scratch DB and verify
	bash scripts/backup/verify-restore.sh

cluster: ## Create kind cluster + add-ons + secrets with Terraform
	cd terraform/environments/local && terraform init -input=false && terraform apply -auto-approve

k8s-deploy: ## Build, load into kind, deploy dev overlay
	bash deployment/scripts/deploy-k8s.sh

bluegreen: ## Blue-green deploy IMAGE=devsecops360-backend:<tag>
	NAMESPACE=$(NS) bash deployment/scripts/blue-green-deploy.sh $(IMAGE)

rollback: ## Instant blue-green rollback
	NAMESPACE=$(NS) bash deployment/rollback/rollback.sh

status: ## Blue/green status
	NAMESPACE=$(NS) bash deployment/scripts/status.sh

chaos: ## Run Kubernetes chaos experiments
	NAMESPACE=$(NS) bash scripts/chaos/kill-pod.sh
	NAMESPACE=$(NS) bash scripts/chaos/db-outage.sh

cluster-destroy: ## Delete the kind cluster
	cd terraform/environments/local && terraform destroy -auto-approve

.PHONY: help env up up-full down nuke logs test test-pg lint smoke e2e load scan backup restore-verify cluster k8s-deploy bluegreen rollback status chaos cluster-destroy
