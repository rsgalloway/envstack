# envstack

envstack is a **stacked environment configuration and activation layer** for tools
and processes.

It provides a deterministic way to **activate environments and compose
configuration hierarchically**, using explicit layering, inheritance, and
overrides.

At its core, envstack is about:
- Environment activation
- Configuration layering
- Policy and precedence
- Making sure tools run with the correct environment

## The problem envstack solves

Real environments are not flat.

They are:
- Hierarchical (base → env → project → task)
- Contextual (dev, prod, CI, local)
- Layered over time
- Full of defaults, overrides, and exceptions

Flat `.env` files don’t model this well. envstack treats environment
configuration as a **stack**: ordered, inspectable, and reproducible.

## Core concepts

### Environment stacks
An environment stack is one or more named environments combined in order.
Stacks define **precedence**: variables flow from higher scope to lower scope,
with explicit overrides.

### Hierarchy and inheritance
Environments can inherit from other environments, forming a hierarchy.
Downstream environments may refine or override upstream values without
duplication.

### Includes
Environment definitions may include other environments declaratively,
allowing shared base configuration to be reused consistently.

### Resolution
Variables can reference other variables, define defaults, or require values
to be set. Resolution is explicit and inspectable before execution.

## What envstack is (and is not)

**envstack is:**
- A configuration layer for environment variables
- An environment activation mechanism
- A system for hierarchical configuration composition

**envstack is not:**
- A dependency resolver
- A package manager
- A runtime isolation tool

envstack focuses on **how environments are composed and activated**, not how
dependencies are installed.

## Typical uses

envstack is commonly used for:
- CLI tools
- Services
- CI/CD pipelines
- Developer workstations
- Pipeline and DCC tooling
- Shared, hierarchical environment configuration

## A simple example

```yaml
ROOT: /mnt/pipe
ENV: ${ENV:=prod}
DEPLOY_ROOT: ${ROOT}/${ENV}
```

```bash
$ envstack -r DEPLOY_ROOT
DEPLOY_ROOT=/mnt/pipe/prod
```
```bash
$ envstack -- echo {DEPLOY_ROOT}
/mnt/pipe/prod
```

## Philosophy

"You want envstack. It’s what .env files wish they were when they grew up."

envstack is intentionally opinionated:

- Explicit over implicit
- Layered over flat
- Inspectable over magical
