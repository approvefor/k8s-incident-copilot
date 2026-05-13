HELM ?= $(shell command -v helm 2>/dev/null)
VENV_PYTHON := $(or $(wildcard .venv/bin/python),$(wildcard .venv/Scripts/python.exe))
SYSTEM_PYTHON := $(or $(shell command -v python3 2>/dev/null),$(shell command -v python 2>/dev/null))
COMPOSE ?= $(shell docker compose version >/dev/null 2>&1 && echo docker compose || (docker-compose version >/dev/null 2>&1 && echo docker-compose))
PYTHON ?= $(or $(VENV_PYTHON),$(SYSTEM_PYTHON))
PYTHON_VENV_PACKAGE ?= $(shell $(SYSTEM_PYTHON) -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}-venv")' 2>/dev/null)
PIP_FLAGS ?= --disable-pip-version-check --no-cache-dir

.PHONY: check-python check-system-python check-test-deps check-compose check-helm setup test evals verify compose-up compose-logs compose-down demo helm-deps helm-lint helm-template helm-lint-prod helm-template-prod

check-python:
	@if [ -z "$(PYTHON)" ]; then \
		echo "Python was not found. Install python3 in WSL: sudo apt update && sudo apt install -y python3 python3-pip python3-venv"; \
		exit 1; \
	fi

check-system-python:
	@if [ -z "$(SYSTEM_PYTHON)" ]; then \
		echo "Python was not found. Install python3 in WSL: sudo apt update && sudo apt install -y python3 python3-pip python3-venv"; \
		exit 1; \
	fi

check-test-deps: check-python
	@$(PYTHON) -c "import pytest, yaml, fastapi, qdrant_client" >/dev/null 2>&1 || { \
		echo "Python dependencies are missing. Run: make setup"; \
		exit 1; \
	}

check-compose:
	@if [ -z "$(COMPOSE)" ]; then \
		echo "Docker Compose was not found. Enable Docker Desktop WSL integration or install: sudo apt install -y docker-compose-plugin"; \
		exit 1; \
	fi

check-helm:
	@if [ -z "$(HELM)" ]; then \
		echo "Helm was not found. Install it before running Helm validation: https://helm.sh/docs/intro/install/"; \
		exit 1; \
	fi

setup: check-system-python
	$(SYSTEM_PYTHON) -m venv --clear .venv || { \
		echo "Could not create .venv. On Ubuntu/WSL install venv support: sudo apt install -y python3-venv $(PYTHON_VENV_PACKAGE)"; \
		exit 1; \
	}
	.venv/bin/python -m pip install $(PIP_FLAGS) --upgrade pip
	.venv/bin/python -m pip install $(PIP_FLAGS) -r requirements-dev.txt

test: check-test-deps
	PYTHONPATH=. $(PYTHON) -m pytest -q

evals: check-test-deps
	PYTHONPATH=. $(PYTHON) scripts/run-evals.py

verify: test evals helm-lint helm-template helm-lint-prod helm-template-prod

compose-up: check-compose
	$(COMPOSE) up --build -d

compose-logs: check-compose
	$(COMPOSE) logs -f api worker

compose-down: check-compose
	$(COMPOSE) down

demo:
	./scripts/demo.sh

helm-deps: check-helm
	$(HELM) dependency update deploy/helm/ai-platform

helm-lint: helm-deps
	$(HELM) lint deploy/helm/ai-platform

helm-template: helm-deps
	$(HELM) template ai-platform deploy/helm/ai-platform > /tmp/ai-sre-copilot-rendered.yaml

helm-lint-prod: helm-deps
	$(HELM) lint deploy/helm/ai-platform -f deploy/helm/ai-platform/values-production.yaml

helm-template-prod: helm-deps
	$(HELM) template ai-platform deploy/helm/ai-platform -f deploy/helm/ai-platform/values-production.yaml > /tmp/ai-sre-copilot-rendered-prod.yaml
