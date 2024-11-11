# =============================================================================
# Project: EnvStack - Environment Variable Management
# Makefile for building project executables on Linux and Windows (using Wine)
#
# Usage:
#   make all       - Builds both Linux and Windows versions
#   make linux     - Builds Linux version only
#   make windows   - Builds Windows version only (requires Wine)
#   make clean     - Removes all build artifacts
#   make install   - Installs the build artifacts using distman
#
# Requirements:
#   - Python and pip installed (Linux)
#   - Wine installed for Windows builds on Linux
#   - distman installed for installation (pip install distman)
# =============================================================================

# Define the installation command
INSTALL_CMD := pip install . -t build

# Define commands for each platform
LINUX_CMD = pip install . -t build/linux -U
WINDOWS_CMD = wine pip install . -t build/windows -U

# Target to build for Linux
linux:
	$(LINUX_CMD)

# Target to build for Windows (using Wine)
windows:
	$(WINDOWS_CMD)

# Combined target to build for both platforms
all: linux windows

# Clean target to remove the build directory
clean:
	rm -rf build

# Install target to install the builds using distman
# using --force allows uncommitted changes to be disted
install:
	distman --force

# Phony targets
.PHONY: all linux-build windows-build clean
