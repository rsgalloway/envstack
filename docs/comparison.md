# Tool Comparison

This document compares **envstack** to related tools and explains how it fits into
a broader tooling ecosystem.

The goal is clarity, not competition. These tools solve different problems and
often work best together.

---

## High-level Comparison

| Tool                  | Per-user envs | Shared envs | Portable | Network-friendly | Complexity |
| --------------------- | - | - | - | - | - |
| **virtualenv / venv** | ✅ Yes | ❌ No | ❌ No | ❌ No | ✅ Low|
| **conda**             | ✅ Yes | ⚠️ Not really | ⚠️ Weak | ⚠️ Mixed | ⚠️ Medium |
| **rez**               | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Heavy |
| **envstack**          | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Low |

---

### conda
conda improves on virtualenv by providing:
- Binary packages
- A dependency solver
- Environment export via YAML

However, conda environments are still:
- Directory-based and stateful
- Sensitive to absolute paths
- Difficult to relocate cleanly
- Poorly suited to concurrent, read-only consumption

conda can be made to work in shared scenarios with careful discipline, but it is
not designed around central publishing and large-scale reuse.

**conda answers:**  
> “How do I manage a reproducible environment for myself or my team?”

---

### rez
rez was explicitly designed to solve **shared, studio-scale environment
management**.

Key properties:
- Immutable, versioned packages
- Read-only consumption
- Explicit dependency graphs
- Network filesystem–first design
- Deterministic activation

rez answers a different question entirely:

> “How do hundreds of users get the same toolchain today—and a different one
> tomorrow—without breaking anything?”

---

## envstack vs dotenv

### dotenv
dotenv provides a simple mechanism for loading key/value pairs from a `.env` file
into a process environment.

Strengths:
- Extremely simple
- Minimal cognitive overhead
- Works well for small, flat configurations

Limitations:
- No native concept of layering or hierarchy
- No explicit precedence model
- Limited reuse or inheritance
- Difficult to scale beyond a single file

---

### envstack
envstack generalizes the `.env` concept into a **stacked, hierarchical configuration
model**.

envstack adds:
- Explicit environment stacks
- Deterministic layering and overrides
- Inheritance and includes
- Variable resolution with defaults and validation
- Inspection and tracing of resolved values

In short:

> dotenv loads a file  
> envstack composes environments

envstack is best suited when configuration must scale across environments,
projects, tools, or users.

---

## envstack vs conda / uv / rez

These tools operate at **different layers**.

### conda / uv
conda and uv focus on:
- Dependency resolution
- Installing packages
- Managing isolated runtimes

They answer:
> “What is installed, and where?”

---

### rez
rez focuses on:
- Package version resolution
- Generating environments from package graphs
- Activating toolchains via environment variables

It answers:
> “Which versions of which packages are active?”

---

### envstack
envstack focuses on:
- Configuration composition
- Environment activation
- Policy and precedence

It answers:
> “How is this environment defined and layered?”

envstack:
- Does **not** solve dependency graphs
- Does **not** install packages
- Does **not** create isolated runtimes

Instead, it provides a clear, inspectable way to define and activate environments,
and can be used alongside tools like conda, uv, or rez—or independently in
curated workflows.

---

## envstack + distman

envstack is often paired with **distman** to form a lightweight, explicit
environment system.

### distman
distman provides:
- Deterministic, versioned deployments
- Reproducible installation locations
- Explicit control over what is installed and where

### envstack
envstack provides:
- Activation of deployed tools
- Hierarchical configuration
- Layered environment composition

Together, they enable a pattern where:
- Tools and libraries are deployed to shared locations
- Environments describe *how* those tools are activated
- Dependencies are curated rather than solver-driven

This model is conceptually similar to rez, but emphasizes:
- Explicit configuration over dependency graphs
- Policy and curation over solver heuristics
- Shared environments over per-tool isolation

envstack and distman can also be used independently:
- envstack for local or ad-hoc configuration
- distman for simple, deterministic deployment

---

## Summary

envstack occupies the **configuration and activation layer**.

It complements tools that install or resolve dependencies, and replaces ad-hoc,
implicit environment management with explicit, inspectable composition—especially
in shared, multi-user environments.
