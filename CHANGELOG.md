# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-02-08

### Added
- Support for using command output as environment variable values
- Inference rules for resolving and validating environment values

### Changed
- Improved path template handling and resolution behavior

### Fixed
- Regression that caused trailing braces to be incorrectly trimmed in some values

### Notes
- This release marks the first stable 1.0 version of envstack.
- CLI behavior, configuration semantics, and resolution rules are now considered stable.

---

## [0.9.6] - 2026-01-11

### Added
- initial docs, citation and changelog files

### Changed
- move test .env files to fixtures
- convert setup.py to pyproject.toml file
- ensure $STACK is always set

### Fixed
- addresses test syntax warnings

---

## [0.9.5] - 2026-01-09

### Added
- support --quiet in envstack shell
- adds make.bat file, smoke test on windows, disable fail-fast tests

### Changed
- updates to envstack banner for exit hints
- only support CAPITALIZED drive letters on windows to avoid path splitting issue
- disable lowercase drive letter tests
- minor updates to cache env file

### Fixed
- fixes for windows: cmd wrapper, argv expansion
- skip cmd tests if not on linux
