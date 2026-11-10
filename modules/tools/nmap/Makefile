MAKEFLAGS += --no-print-directory

ROOT_DIR := $(abspath $(CURDIR)/../../..)
LOG_DIR ?= $(ROOT_DIR)/.make-logs/modules/tools/nmap

# Nmap uses an upstream image by default (instrumentisto/nmap). No local build needed.
.PHONY: build

build:
	@mkdir -p "$(LOG_DIR)"
	@echo "nmap: no local image build (uses upstream container)"
