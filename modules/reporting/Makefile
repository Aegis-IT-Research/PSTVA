MAKEFLAGS += --no-print-directory

ROOT_DIR := $(abspath $(CURDIR)/../..)
LOG_DIR ?= $(ROOT_DIR)/.make-logs/modules/reporting

-include $(ROOT_DIR)/.env
export

REPORT_BUILDER_IMAGE ?= pentest-report-builder:latest

NO_CACHE ?= 0
NO_CACHE_FLAG := $(if $(filter 1 true TRUE yes YES,$(NO_CACHE)),--no-cache,)

.PHONY: build

build:
	@mkdir -p "$(LOG_DIR)"
	docker build $(NO_CACHE_FLAG) --progress plain --tag $(REPORT_BUILDER_IMAGE) -f $(ROOT_DIR)/modules/reporting/reportbuilder/docker/Dockerfile $(ROOT_DIR)/modules/reporting
