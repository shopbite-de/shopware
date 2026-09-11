ifndef APP_ENV
	include .env
endif

.DEFAULT_GOAL := help
.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z-]+:.*?## .*$$/ {printf "[32m%-15s[0m %s\n", $$1, $$2}' Makefile | sort

###> shopware/docker-dev ###
up:
	@touch .env.local
	docker compose --env-file .env.local up -d
stop:
	docker compose stop
down:
	docker compose down
shell:
	docker compose exec web bash
watch-storefront:
	docker compose exec -e PROXY_URL=http://localhost:9998 web ./bin/watch-storefront.sh
watch-admin:
	docker compose exec web ./bin/watch-administration.sh
build-storefront:
	docker compose exec web ./bin/build-storefront.sh
build-administration:
	docker compose exec web ./bin/build-administration.sh
setup:
	docker compose exec web bin/console system:install --basic-setup --create-database --drop-database --force
###< shopware/docker-dev ###

###> shopbite/docker-prod ###
# Production image + stack. Configure docker/prod.env (see docker/prod.env.example).
comma := ,
-include docker/prod.env
export SHOPWARE_PACKAGES_TOKEN
IMAGE ?= shopbite/shopware
TAG ?= latest
PHP_VERSION ?= 8.4
PROD_COMPOSE := docker compose -f compose.prod.yaml --env-file docker/prod.env
BUILD_SECRETS := $(if $(wildcard auth.json),--secret id=composer_auth$(comma)src=auth.json)
ifneq ($(strip $(SHOPWARE_PACKAGES_TOKEN)),)
BUILD_SECRETS += --secret id=packages_token$(comma)env=SHOPWARE_PACKAGES_TOKEN
endif

prod-build: ## Build the production image (pulls the latest base images for PHP security fixes)
	docker build --pull -f docker/Dockerfile --build-arg PHP_VERSION=$(PHP_VERSION) $(BUILD_SECRETS) -t $(IMAGE):$(TAG) .
prod-up: ## Start or update the production stack (runs the Deployment Helper first)
	$(PROD_COMPOSE) up -d --remove-orphans
prod-deploy: prod-build prod-up ## Rebuild image and roll it out
prod-down: ## Stop the production stack (volumes are kept)
	$(PROD_COMPOSE) down
prod-logs: ## Follow logs of the production stack
	$(PROD_COMPOSE) logs -f --tail=200
prod-ps: ## Show production container status
	$(PROD_COMPOSE) ps
prod-shell: ## Shell into the production web container
	$(PROD_COMPOSE) exec web bash
prod-console: ## Run bin/console in production, e.g. make prod-console cmd="cache:clear"
	$(PROD_COMPOSE) exec web bin/console $(cmd)
prod-config: ## Render the resolved production compose config
	$(PROD_COMPOSE) config
###< shopbite/docker-prod ###
