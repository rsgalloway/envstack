# Frequently Asked Questions

This document answers common questions, design tradeoffs, and sharp edges in
envstack.

The answers are intentionally direct and opinionated.

## Why not just use `.env` files?

Flat `.env` files do not scale.

They lack:
- Hierarchy
- Inheritance
- Explicit precedence
- Reuse without duplication

envstack exists to model real-world environment configuration, which is almost
always layered and contextual.

## Why not just use dotenv?

dotenv loads a file.

envstack composes environments.

If you need layering, inheritance, or inspection, envstack is a better fit.

## Why doesn’t envstack install dependencies?

Because that is a different problem.

envstack intentionally does not:
- Install packages
- Resolve dependency graphs
- Manage runtimes

Those concerns are handled by other tools. envstack focuses on **activation and
configuration**, not installation.

## Is envstack a replacement for conda / rez / uv?

No - and sometimes yes.

envstack does not solve dependency graphs or create isolated runtimes. However,
envstack is often used *alongside* or *on top of* those tools.

In curated environments (e.g. shared network deployments), envstack can replace
solver-driven tools by activating pre-built, versioned environments explicitly.

The difference is **policy vs solver**.

## How does envstack handle versioning?

envstack itself does not version dependencies.

Versioning is handled by:
- Deployment tooling (e.g. distman)
- Directory layout
- Revision control systems
- Higher-precedence overrides

envstack activates whatever it is pointed at.

## How does envstack compare to rez?

rez models environments as the result of a package graph.

envstack models environments as explicit configuration layers.

Both approaches are valid. envstack favors:
- Explicit configuration
- Predictable overrides
- Simpler mental models

## Can envstack manage shared environments?

Yes.

envstack works well with shared, network-deployed environments where:
- Tools and libraries live in deterministic locations
- Environments describe how to activate them
- Multiple tools share common configuration

This is a common pattern in pipeline and facility environments.

## Does envstack provide runtime isolation?

envstack can provide isolation, but it is **policy-defined rather than
runtime-enforced**.

All environment systems ultimately resolve to files on disk and environment
variables. envstack is no different.

If an envstack environment points at versioned, immutable directories and
excludes other paths, then tools activated under that environment are effectively
isolated.

The difference is where the isolation contract lives:

- envstack relies on explicit configuration and directory layout
- Other systems may enforce isolation via prefixes, resolvers, or runtimes

envstack makes isolation **visible and intentional**, rather than implicit.

## Why doesn’t envstack freeze environments per tool?

Because envstack intentionally resolves environments **at activation time**.

In envstack, environments are not snapshots. They are composed dynamically
each time a tool is activated.

This means:
- Shared environments can evolve over time
- Updates propagate automatically on the next invocation
- Tools intentionally pick up new versions when they are deployed
- Rollbacks and pinning are handled by policy and configuration, not rebuilds

This late-binding model is well-suited to:
- Shared network environments
- Facility or pipeline tooling
- Centralized deployments with controlled updates

envstack prioritizes **explicit activation and policy-driven updates** over
frozen, per-tool runtime snapshots.

## When might envstack not be a good fit?

envstack may not be a good fit if you require:
- Runtime-enforced isolation guarantees
- Automatic dependency resolution
- A closed-world execution model

envstack favors explicit, policy-driven environments over enforced sandboxes.

## Does envstack support secrets?

envstack supports encrypting environment values and resolving them at runtime.

However, envstack is not a secrets manager. It does not:
- Rotate secrets
- Enforce access control
- Manage secret lifecycles

Use a dedicated secrets system when those guarantees are required.

## Is envstack cross-platform?

Yes.

envstack supports platform-specific configuration and works on Linux, macOS,
and Windows. Platform differences must still be modeled explicitly.

## Why is envstack opinionated?

Because unopinionated configuration systems tend to accumulate complexity
without structure.

envstack encodes a specific set of tradeoffs to keep environments understandable
over time.

## What are the sharp edges?

Some things to be aware of:

- envstack is explicit by design; it will not guess intent
- Order matters - precedence is determined by stack order
- Misordered stacks can produce surprising results
- Shared environments require discipline and conventions
- Debugging configuration still requires thought (envstack just makes it visible)

envstack will not protect you from bad policy - it will make it obvious.

## Summary

envstack is designed for **explicit, late-bound environment activation**.

It prioritizes:
- Clear, inspectable configuration
- Hierarchical composition
- Policy-driven updates
- Runtime activation over frozen snapshots

envstack intentionally does not enforce hard runtime isolation or automatic
dependency freezing. Environments are resolved at activation time, allowing shared
environments to evolve and tools to pick up updates intentionally.

If you value explicit control, clarity, and shared configuration over
per-tool sandboxing, envstack is a good fit.
