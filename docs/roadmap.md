# Roadmap

This document tracks likely near-term improvements and areas we want to
explore as envstack evolves.

## Near-term backlog

The following items are active candidates for near-term roadmap work:

- API documentation source structure
- ternary-style expansion modifier
- regex expansion modifier
- version tag support

## Performance and benchmarking

envstack now has lightweight performance regression coverage, but it does not
yet have dedicated A/B benchmark tooling that compares base and candidate
changes on the same runner.

This is likely worth adding soon, especially before larger changes to
environment resolution, shell startup, or subprocess wrapping.

Two possible directions:

- Build custom benchmark tools tailored to envstack, similar to the benchmark
  utilities used in sibling projects like `pyseq` and `snapfs`
- Evaluate an off-the-shelf benchmark framework such as `asv` for repeatable
  performance tracking over time

Initial benchmark candidates:

- stack loading and environment resolution
- repeated `envstack -- [COMMAND]` subprocess startup cost
- shell launch overhead
- variable tracing and path expansion on larger environment stacks

Future benchmark work should ideally cover both:

- one-off profiling for targeted optimization work
- regression checks that help catch performance drift across releases

The next benchmark milestone should be same-VM branch-vs-base comparisons,
similar to the workflow used in `pyseq`, so we can catch smaller regressions in
the `5-10%` range with less runner noise.
