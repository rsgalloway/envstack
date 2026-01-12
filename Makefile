# =============================================================================
# Project: EnvStack - Environment Variable Management
# Makefile for building project executables on Linux
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
BUILD_CMD := python -m pip install . -t $(BUILD_DIR)

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
	rm -rf build/bin build/lib build/envstack build/bdist* build/__pycache__

# Combined target to build for both platforms
all: build

# Test target to verify the build
test:
	$(ENVSTACK_CMD) -- ls -al
	${ENVSTACK_CMD} -- which python

# Install dryrun target to simulate installation
dryrun:
	$(ENVSTACK_CMD) -- dist --dryrun

# Install target to install the builds using distman
# using --force allows uncommitted changes to be disted
install: build
	dist --force --yes

# Phony targets
.PHONY: build dryrun install clean
