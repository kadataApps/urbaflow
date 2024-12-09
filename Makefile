.PHONY: help start-postgis stop-postgis build-urbaflow urbaflow dev update-python-dependencies

start-postgis: ## Start a postgis server as a daemon, exposed on port 5432
	docker compose up -d postgis

stop-postgis: ## Stop the postgis server daemon
	docker compose stop postgis


urbaflow: ## Run bash environment with available python dependencies for data urbaflow
	docker compose -f docker-compose.yml run --rm urbaflow /bin/bash


# DEV COMMANDS
build-urbaflow:
	docker compose build urbaflow

dev: ## mount the urbaflow folder and run bash environment with available python dependencies for data urbaflow
	docker compose run --rm urbaflow /bin/bash

lint:
	poetry run ruff check
	poetry run ruff format

update-python-dependencies:
	poetry export --without-hashes -o requirements.txt



help:
		@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
