# =============================================================================
# Project: EnvStack - Environment Variable Management
# Makefile for building project executables on Linux and Windows (using Wine)
#
# Usage:
#   make           - Builds targets
#   make clean     - Removes all build artifacts
#   make install   - Installs the build artifacts using distman
#
# Requirements:
#   - Python and pip installed (Linux)
#   - Wine installed for Windows builds on Linux
#   - distman installed for installation (pip install distman)
# =============================================================================

# Define the installation command
BUILD_CMD := pip install . -t build

# Target to build for Linux
build:
	$(BUILD_CMD)

# Combined target to build for both platforms
all: build

# Clean target to remove the build directory
clean:
	rm -rf build

# Install target to install the builds using distman
# using --force allows uncommitted changes to be disted
install:
	distman --force --yes

# Phony targets
.PHONY: build install clean
