# Automatically mark all targets as .PHONY
PHONY_TARGETS := $(shell \
	grep -E '^[a-zA-Z0-9_-]+:' Makefile | \
	cut -d: -f1 \
)
.PHONY: $(PHONY_TARGETS)


SHELL := /bin/bash
SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# Better print messages, removes: "make[1]: Entering directory"
MAKEFLAGS += --no-print-directory

# Logs
LOGS_ROOT ?= $(CURDIR)/.make-logs

# Env variables
export DOCKER_CMD := $(shell command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose)
export DOCKER_GID := $(shell getent group docker | cut -d: -f3)

# First run: create .env from the template (make re-reads it after creating it)
.env:
	cp .env.example .env
	@echo "Created .env from .env.example. Change the passwords and JWT_SECRET in it."

-include .env
export


# -------------------------
# Modular sub-make support
# -------------------------
# Discover subprojects by locating Makefiles under the repo (excluding root).
SUB_MAKEFILES := $(shell find . -mindepth 2 -name Makefile \
	-not -path './.git/*' \
	-not -path './.venv/*' \
	-not -path './**/.venv/*' \
	-not -path './node_modules/*' \
	-not -path './**/node_modules/*')
SUB_MAKE_DIRS := $(sort $(patsubst ./%,%,$(dir $(SUB_MAKEFILES))))

define _run_submake_target_tolerant
	@fail=0; \
	for d in $(SUB_MAKE_DIRS); do \
		d=$${d%/}; \
		log_dir="$(LOGS_ROOT)/$$d"; \
		log_file="$$log_dir/$(1).log"; \
		mkdir -p "$$log_dir"; \
		echo "==> $$d: $(1) (log: $$log_file)"; \
		$(MAKE) -C "$$d" $(1) LOG_DIR="$$log_dir" NO_CACHE="$(NO_CACHE)" >"$$log_file" 2>&1 || { \
			echo "!! FAILED: $$d (see $$log_file)"; \
			fail=1; \
		}; \
	done; \
	if [ $$fail -ne 0 ]; then \
		echo "\nSome modules failed. Inspect logs under $(LOGS_ROOT)/"; \
	fi; \
	exit 0
endef

define _run_submake_target_strict
	@fail=0; \
	for d in $(SUB_MAKE_DIRS); do \
		d=$${d%/}; \
		log_dir="$(LOGS_ROOT)/$$d"; \
		log_file="$$log_dir/$(1).log"; \
		mkdir -p "$$log_dir"; \
		echo "==> $$d: $(1) (log: $$log_file)"; \
		$(MAKE) -C "$$d" $(1) LOG_DIR="$$log_dir" NO_CACHE="$(NO_CACHE)" >"$$log_file" 2>&1 || { \
			echo "!! FAILED: $$d (see $$log_file)"; \
			fail=1; \
		}; \
	done; \
	if [ $$fail -ne 0 ]; then \
		echo "\nSome modules failed. Inspect logs under $(LOGS_ROOT)/"; \
	fi; \
	exit $$fail
endef


ifeq ($(MESSAGE_PRINTED_ONCE),)

$(info $(shell clear))

$(info ╔═════════════════════════════════════════════════════════════════╗)
$(info ║      + +  +                                                     ║)
$(info ║    +  ++++  +   +     0   +++++     +   +     +   +        +    ║)
$(info ║  +         /    +     |   +     +   +   +     |   ++      ++    ║)
$(info ║   ++            +     +   +     +   +   +  0  +   +  +  +  +    ║)
$(info ║  +  +           +     +   + ===+    +   +  |  +   |   ++   +    ║)
$(info ║   +   ++++ \     +++++    +     '0  +    +++++    o        +    ║)
$(info ║      +  ++                                                      ║)
$(info ║                     ___  ____ ___ _  _ ____                     ║)
$(info ╚════════════════════ |__] [__   |  |  | |__| ════════════════════╝)
$(info .                     |    ___]  |   \/  |  |                     .)

$(info )

export MESSAGE_PRINTED_ONCE := 1
endif


# Targets
help: ## > Show this help. (generated from comments using specific prefix)
	@sed -ne '/@sed/!s/## //p' $(MAKEFILE_LIST)  | awk '{$$1=$$1}1' | column -t -s ">" -o "  "

discover: ## > List discovered sub-Makefiles
	@echo "Discovered Makefiles:"; \
	for d in $(SUB_MAKE_DIRS); do echo "- $$d"; done

confirm:
	@read -p "Are you sure? [y/N] " ans; \
	if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
		echo "Confirmed!"; \
	else \
		echo "Aborted."; \
		exit 1; \
	fi

install-docker:
	sh core/infra/scripts/install-docker.sh

build-front:  ## > Build front end
	@$(MAKE) -C modules/frontend build

build-back:  ## > Build back end
	@$(MAKE) -C core build

build-all:  ## > Build all services (strict)
	@$(MAKE) build-all-strict

build-all-strict: ## > Build all services and fail on any error
	@$(MAKE) build-core
	@$(MAKE) build-modules-strict

build-all-tolerant: ## > Build all services and continue on module errors
	@$(MAKE) build-core
	@$(MAKE) build-modules

build-all-nocache: ## > Build all services without Docker cache (strict)
	@$(MAKE) build-core NO_CACHE=1
	@$(MAKE) build-modules-strict NO_CACHE=1

build-core: ## > Build only core
	@log_dir="$(LOGS_ROOT)/core"; \
	log_file="$$log_dir/build.log"; \
	mkdir -p "$$log_dir"; \
	echo "==> core: build (log: $$log_file)"; \
	$(MAKE) -C core build LOG_DIR="$$log_dir" NO_CACHE="$(NO_CACHE)" >"$$log_file" 2>&1 || { \
		echo "!! FAILED: core (see $$log_file)"; \
		exit 1; \
	}

build-core-nocache: ## > Build only core without Docker cache
	@$(MAKE) build-core NO_CACHE=1

build-modules: ## > Build all modules/tools that have a Makefile (tolerant)
	$(call _run_submake_target_tolerant,build)

build-modules-nocache: ## > Build all modules/tools without Docker cache (tolerant)
	@$(MAKE) build-modules NO_CACHE=1

build-modules-strict: ## > Build all modules/tools and fail if any fail
	$(call _run_submake_target_strict,build)

build-reporting-mod:  ## > Build reporting module image (ReportBuilder; transitional)
	@$(MAKE) -C modules/reporting build

build-tool-kerbrute:  ## > Build Kerbrute tool image (transitional)
	@$(MAKE) -C modules/tools/kerbrute build

build-tool-adenum:  ## > Build ADEnum tool image (transitional)
	@$(MAKE) -C modules/tools/adenum build

start:  ## > Start all the services
	${DOCKER_CMD} -f core/infra/compose.yml up -d
	@echo "\nVisit: ${AUTO_HOST} with your browser\n"

start-core:  ## > Start services using core/infra compose
	${DOCKER_CMD} -f core/infra/compose.core.yml up -d
	@echo "\nVisit: ${AUTO_HOST} with your browser\n"

start-core-frontend:  ## > Start core + frontend module
	${DOCKER_CMD} -f core/infra/compose.core.yml -f core/infra/compose.modules.yml --profile frontend up -d
	@echo "\nVisit: ${AUTO_HOST} with your browser\n"

start-core-flower:  ## > Start core + Flower module
	${DOCKER_CMD} -f core/infra/compose.core.yml -f core/infra/compose.modules.yml --profile flower up -d
	@echo "\nVisit: ${AUTO_HOST} with your browser\n"

start-core-full:  ## > Start core + all current modules
	${DOCKER_CMD} -f core/infra/compose.core.yml -f core/infra/compose.modules.yml --profile frontend --profile flower up -d
	@echo "\nVisit: ${AUTO_HOST} with your browser\n"

start-core-open:  ## > Start services using core/infra compose with open ports
	${DOCKER_CMD} -f core/infra/compose.core.yml -f core/infra/compose.openports.yml up -d
	@echo "\nVisit: ${AUTO_HOST} with your browser\n"

stop:  ## > Stop all the services
	${DOCKER_CMD} -f core/infra/compose.yml down

stop-core:  ## > Stop services started with core/infra compose
	${DOCKER_CMD} -f core/infra/compose.core.yml down

stop-core-full:  ## > Stop core + modules started with core/infra compose
	${DOCKER_CMD} -f core/infra/compose.core.yml -f core/infra/compose.modules.yml down

LOG_SERVICES ?=
CORE_LOG_SERVICES ?=
LOG_TAIL ?= 200

logs:  ## > Show logs for services (override LOG_SERVICES to filter)
	${DOCKER_CMD} -f core/infra/compose.yml logs -f --tail=${LOG_TAIL} ${LOG_SERVICES}

logs-all: ## > Follow logs for all compose services
	${DOCKER_CMD} -f core/infra/compose.yml logs -f --tail=${LOG_TAIL}

logs-back: ## > Follow backend API logs
	${DOCKER_CMD} -f core/infra/compose.yml logs -f --tail=${LOG_TAIL} back

logs-worker: ## > Follow Celery worker logs
	${DOCKER_CMD} -f core/infra/compose.yml logs -f --tail=${LOG_TAIL} worker

logs-traefik: ## > Follow Traefik logs
	${DOCKER_CMD} -f core/infra/compose.yml logs -f --tail=${LOG_TAIL} traefik

logs-core:  ## > Show logs using core/infra compose (override CORE_LOG_SERVICES to filter)
	${DOCKER_CMD} -f core/infra/compose.core.yml logs -f --tail=${LOG_TAIL} ${CORE_LOG_SERVICES}

boot-start:  ## > * --- Start Here --- * Build, start, show logs
	@$(MAKE) build-all
	@$(MAKE) start
	@$(MAKE) logs

