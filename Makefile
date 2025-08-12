# =============================================================================
# Project: EnvStack - Environment Variable Management
# Makefile for building project executables on Linux and Windows (using Wine)
#
# Usage:
#   make           - Builds targets
#   make clean     - Removes all build artifacts
#   make dryrun    - Simulates installation without making changes
#   make install   - Installs the build artifacts using distman
#
# Requirements:
#   - Python and pip installed (Linux)
#   - Wine installed for Windows builds on Linux
#   - distman installed for installation (pip install distman)
# =============================================================================

# Define the installation command
BUILD_DIR := build
BUILD_CMD := pip install -r requirements.txt -t $(BUILD_DIR)

# envstack command uses ./env for ENVPATH
ENVSTACK_CMD := ENVPATH=$(CURDIR)/env \
                PATH=$(CURDIR)/bin:$(BUILD_DIR)/bin:$$PATH \
                PYTHONPATH=$(CURDIR)/lib:$(BUILD_DIR):$$PYTHONPATH \
                envstack ${PROJECT} ${ENV}

# Clean target to remove the build directory
clean:
	rm -rf build

# Target to build for Linux
build: clean
	$(BUILD_CMD)

# Combined target to build for both platforms
all: build

# Install dryrun target to simulate installation
test:
	$(ENVSTACK_CMD) -- l {ROOT}

# Install dryrun target to simulate installation
dryrun:
	$(ENVSTACK_CMD) -- distman --dryrun

# Install target to install the builds using distman
# using --force allows uncommitted changes to be disted
install: build
	distman --force --yes

# Phony targets
.PHONY: build dryrun install clean
