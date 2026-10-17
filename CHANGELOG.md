# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.0.5] - 2026-10-17

### Removed

- remove the unused CLI `--scope` option (#131). Use `ENVPATH` to select stack search directories; the Python API `scope` parameter remains supported.
- remove the legacy `envstack.path` API (`Path`, `Template`, `get_scope`, `get_template`, `match_template`, and `extract_fields`), its unused `env.Scope` wrapper, and path-only exceptions (#132). Use `pathlib` or `os.path` for filesystem operations and application-owned code for path templating; stack discovery continues to use `ENVPATH` and the current directory or explicit scope.

### Changed

- use `DEFAULT_NAMESPACE` as the environment setting for the default stack name
- allow `-u`/`--unresolved` to select zero or more variables, matching `-r`/`--resolve`, with `-q` for a single value. Put stack names before the option: replace `envstack -u dev` with `envstack dev -u`.

### Added

- document expansion, YAML transformation timing, runtime controls, and current name-collision behavior, with a composed example (#125)
- add NumPy, Pillow, and OpenEXR examples demonstrating accumulated search paths and runtime selection of NumPy builds
- add a standalone PySide6 example with a small GUI application
- add installation guides and distman manifests aligned with the examples' deployment paths
- add regression coverage for shared includes, tool-root overrides, and accumulation of `PATH`, `PYTHONPATH`, and custom search variables

### Fixed

- preserve explicit empty strings when referenced, overriding included and shell values; empty assignments reset accumulated paths
- retain `:=` assignments for subsequent references to explicitly empty variables
- keep self-default assignments local to their definition so inherited defaults do not shadow final values
- respect variables deleted from a loaded environment instead of restoring them from source history
- accumulate self-references across included stacks and multiple stack arguments, using the previous stack value before falling back to the shell (#140)
- preserve the selected platform when resolving inherited stack values and normalizing path lists
- fix inheritance test expectations for Windows path delimiters and exercise Windows normalization on other hosts

---

## [1.0.4] - 2026-07-25

### Added
- add a `dev` extra with `pytest`, `black`, `isort`, and `flake8` for one-command local setup
- add lightweight performance regression tests using example-based environment fixtures
- add a GitHub Pages docs publishing workflow and a generated docs-site builder

### Changed
- move pytest configuration into `pyproject.toml`
- broaden CI lint checks to cover the full `bin/` directory
- simplify the docs landing page so the published site acts more like a lightweight home page that links to deeper documentation

### Fixed
- restore AES-GCM compatibility on Python 3.8/current `cryptography` by passing an explicit backend where required
- restore the missing `envstack.wrapper` module to release artifacts by cleaning up release/build hygiene
- make plain `pytest tests -q` work reliably via test-suite bootstrap and shared test helpers

---

## [1.0.3] - 2026-07-23

### Changed
- add Python 3.14 to the GitHub Actions test matrix
- update published Python version classifiers through 3.14
- constrain `cryptography` to `<47` on Python 3.8 while allowing newer runtimes to resolve current releases
- limit pytest discovery to the `tests/` suite and ignore `tmp/` helper files

### Fixed
- restore Python 3.14 compatibility in `EnvVar.vars()` by avoiding `string.Template` pattern access that now raises under 3.14
- suppress the `cryptography` Python 3.8 deprecation warning during import so `envstack` subprocess tests and CLI startup remain quiet on supported 3.8 installs

### Notes
- The `1.0.3` PyPI release published on July 23, 2026 was yanked because the distributed wheel/sdist omitted `envstack.wrapper`, which breaks CLI startup after `pip install envstack`.
- Use `1.0.4` or newer instead.

---

## [1.0.2] - 2026-04-01

### Changed
- add a self-contained `make test` target that installs `pytest` and the package in editable mode before running the test suite
- mark `all` as a phony Make target to avoid filename collisions

### Fixed
- remove `return` statements from `finally` blocks in encryption helpers to avoid newer Python `SyntaxWarning`s
- harden optional `cryptography` imports with a decorator-based availability guard so missing crypto dependencies raise a clear runtime error instead of `NoneType` failures

---

## [1.0.1] - 2026-02-08

### Fixed
- SyntaxWarning: invalid escape sequence in envstack shell

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
