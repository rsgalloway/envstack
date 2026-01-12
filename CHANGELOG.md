# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
