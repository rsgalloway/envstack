<p align="left">
  <img src="assets/envstack.png" alt="envstack logo" width="400">
</p>

envstack is an **environment variable composition and activation layer** for
tools and processes.

It is built for cases where environments are hierarchical, shared, and
context-dependent, and where a flat `.env` file stops being enough.

```bash
export ENVPATH=studio/base:show/foo:tool/nuke/14
envstack -- nuke
```

## Why envstack

envstack is a lightweight CLI and Python library for composing, tracing,
exporting, and reproducing environment variables using a PATH-like model
called `ENVPATH`.

### Compose

- Hierarchical environment layers
- Ordered precedence and overrides
- Cross-platform environment activation

### Explain

- Trace variable origins
- Inspect unresolved values
- Debug stack ordering and overrides

### Export

- Bake resolved environments
- Export to shell formats
- Reproduce environments deterministically

## ENVPATH

`ENVPATH` defines **where** environment fragments are discovered and **in what
order** they apply, similar to `PATH`, but for full environments.

```bash
export ENVPATH=prod/base:prod/show/foo:prod/tools/nuke14
envstack -- nuke
```

Later entries can layer on top of earlier ones through includes, hierarchy, and
explicit precedence rules.

## envstack is not

- A dependency solver
- A package manager
- A virtualenv replacement
- A build system

It is intentionally boring: explicit inputs, deterministic outputs, and tooling
that tells you what it did.

## Install

```bash
pip install -U envstack
```

## Quickstart

Inspect the unresolved environment:

```bash
envstack -u
```

Resolve a specific variable:

```bash
envstack -r DEPLOY_ROOT
```

Run a command inside the active stack:

```bash
envstack -- echo {VAR}
```

Trace where a variable comes from:

```bash
envstack -t PATH
```

## Learn More

- [Design](design.md): mental model, hierarchy, and precedence
- [Examples](examples.md): common patterns and stack layouts
- [Secrets](secrets.md): encrypted values and key handling
- [Comparison](comparison.md): how envstack differs from adjacent tools
- [FAQ](faq.md): operational details and gotchas
- [API](api.md): Python and CLI reference material
- [Roadmap](roadmap.md): planned improvements and future work
