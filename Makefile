.PHONY: help up down build test clean lint install dev

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Start all services with docker-compose
	docker-compose up --build -d
	@echo "Services starting..."
	@echo "API: http://localhost:8000"
	@echo "Dashboard: http://localhost:8501"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000"

down: ## Stop all services
	docker-compose down

build: ## Build Docker images
	docker-compose build

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ --cov=src --cov-report=html --cov-report=term

lint: ## Run linters
	flake8 src/ tests/ --max-line-length=120 --ignore=E203,W503
	pylint src/ --max-line-length=120

install: ## Install dependencies
	pip install -r requirements.txt

dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-cov flake8 pylint

clean: ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".pytest_cache" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ dist/ build/ *.egg-info
	rm -f violations.csv

logs: ## View docker-compose logs
	docker-compose logs -f

logs-api: ## View API logs
	docker-compose logs -f api

logs-dashboard: ## View dashboard logs
	docker-compose logs -f dashboard

restart: ## Restart all services
	docker-compose restart

status: ## Show service status
	docker-compose ps

shell-api: ## Open shell in API container
	docker-compose exec api /bin/bash

shell-dashboard: ## Open shell in dashboard container
	docker-compose exec dashboard /bin/bash

generate-data: ## Generate synthetic data for testing
	python -c "from src.data.generator import SyntheticStoreGenerator; import json; g = SyntheticStoreGenerator(); records = g.generate_batch(100); print(json.dumps(records[:5], indent=2))"

validate: ## Validate data contracts
	python -c "from src.data.contracts import DataContractValidator; print('Data contracts loaded successfully')"

.FORCE:

