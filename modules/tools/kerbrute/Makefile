MAKEFLAGS += --no-print-directory

ROOT_DIR := $(abspath $(CURDIR)/../../..)
LOG_DIR ?= $(ROOT_DIR)/.make-logs/modules/tools/kerbrute

KERBRUTE_IMAGE ?= kerbrute-tool:latest

NO_CACHE ?= 0
NO_CACHE_FLAG := $(if $(filter 1 true TRUE yes YES,$(NO_CACHE)),--no-cache,)

.PHONY: build

build:
	@mkdir -p "$(LOG_DIR)"
	docker build $(NO_CACHE_FLAG) --progress plain --tag $(KERBRUTE_IMAGE) $(ROOT_DIR)/modules/tools/kerbrute/docker/
