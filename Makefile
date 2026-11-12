.PHONY: install test lint run-erp run-api up

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .
	ruff format --check .

run-erp:
	uvicorn integration_lab.mock_erp:app --reload --port 8001

run-api:
	uvicorn integration_lab.main:app --reload --port 8000

up:
	docker compose up --build
