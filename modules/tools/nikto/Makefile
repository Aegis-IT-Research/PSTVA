MAKEFLAGS += --no-print-directory

ROOT_DIR := $(abspath $(CURDIR)/../../..)
LOG_DIR ?= $(ROOT_DIR)/.make-logs/modules/tools/nikto

# Nikto uses an upstream image by default (frapsoft/nikto). No local build needed.
.PHONY: build

build:
	@mkdir -p "$(LOG_DIR)"
	@echo "nikto: no local image build (uses upstream container)"
