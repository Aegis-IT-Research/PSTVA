MAKEFLAGS += --no-print-directory

ROOT_DIR := $(abspath $(CURDIR)/..)
LOG_DIR ?= $(ROOT_DIR)/.make-logs/core

# Prefer docker compose v2 if available
DOCKER_CMD := $(shell command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose)
DOCKER_GID := $(shell getent group docker | cut -d: -f3)

-include $(ROOT_DIR)/.env
export

NO_CACHE ?= 0
NO_CACHE_FLAG := $(if $(filter 1 true TRUE yes YES,$(NO_CACHE)),--no-cache,)

.PHONY: build build-back start stop logs

build: build-back

build-back:
	@mkdir -p "$(LOG_DIR)"
	docker build $(NO_CACHE_FLAG) --build-arg DOCKER_GID=$(DOCKER_GID) --progress plain --tag ${BACK_END_IMAGE} -f $(ROOT_DIR)/core/Dockerfile $(ROOT_DIR)

start:
	@mkdir -p "$(LOG_DIR)"
	$(DOCKER_CMD) -f $(ROOT_DIR)/core/infra/compose.core.yml up -d

stop:
	$(DOCKER_CMD) -f $(ROOT_DIR)/core/infra/compose.core.yml down

logs:
	$(DOCKER_CMD) -f $(ROOT_DIR)/core/infra/compose.core.yml logs -f
