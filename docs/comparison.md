# Tool Comparison

This document compares envstack to related tools and explains how it fits into
a broader tooling ecosystem.

The goal is clarity, not competition. These tools solve different problems and
often work best together.

## envstack vs dotenv

### dotenv
dotenv provides a simple mechanism for loading key/value pairs from a `.env`
file into a process environment.

Strengths:
- Extremely simple
- Minimal cognitive overhead
- Works well for small, flat configurations

Limitations:
- No native concept of layering or hierarchy
- No explicit precedence model
- Limited support for reuse or inheritance
- Difficult to scale beyond a single `.env` file

### envstack
envstack generalizes the `.env` concept into a **stacked, hierarchical
configuration model**.

envstack adds:
- Explicit environment stacks
- Deterministic layering and overrides
- Inheritance and includes
- Variable resolution with defaults and validation
- Inspection and tracing of values

In short:

> dotenv loads a file  
> envstack composes environments

envstack is best suited when configuration must scale across environments,
projects, or tools.

## envstack vs conda / uv / rez

These tools operate at a different layer.

### conda / uv
conda and uv focus on:
- Dependency resolution
- Installing packages
- Managing isolated runtimes

They answer:
> “What is installed, and where?”

### rez
rez focuses on:
- Package version resolution
- Generating environments from package graphs
- Activating toolchains via environment variables

It answers:
> “Which versions of which packages are active?”

### envstack
envstack focuses on:
- Configuration composition
- Environment activation
- Policy and precedence

It answers:
> “How is this environment defined and layered?”

envstack does **not**:
- Solve dependency graphs
- Install packages
- Create isolated runtimes

envstack can be used alongside these tools or independently in workflows where
dependencies are curated rather than solved dynamically.

## envstack + distman

envstack is often paired with **distman** to form a lightweight, explicit
environment system.

### distman
distman provides:
- Deterministic, versioned deployments
- Reproducible installation locations
- A simple model for distributing tools and libraries

### envstack
envstack provides:
- Activation of deployed tools
- Hierarchical configuration
- Layered environment composition

Together, they enable a pattern where:
- Tools and libraries are deployed to shared locations
- Environments describe *how* those tools are activated
- Dependencies are expressed as named, include-able environment modules

This model is conceptually similar to rez, but emphasizes:
- Explicit configuration over package graph resolution
- Policy and curation over solver-driven dependency management
- Shared environments over per-tool isolation

envstack and distman can also be used independently:
- envstack without distman for local or ad-hoc configuration
- distman without envstack for simple deployment scenarios

## Summary

envstack occupies the configuration and activation layer.

It complements tools that install or resolve dependencies, and it replaces
ad-hoc, implicit environment management with explicit, inspectable composition.
