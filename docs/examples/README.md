# Examples

The example stacks under `examples/` are now documented here as first-class
guides for the canonical docs site.

Start with the default example, then branch into project activation,
encryption, or wrappers depending on the workflow you need.

## Guides

- [Default example](default.md): base stacks, inheritance, structured values,
  executable stacks, and command substitution with `test.env`
- [Project example](project.md): project-scoped path layouts driven by the
  active stack name
- [Encryption example](encryption.md): key generation, encrypted nodes, and
  decryptable values in versioned stack files
- [Wrappers](wrappers.md): launcher scripts that always run a command inside a
  known stack, including the `bin/hello` example

## Repository Layout

- [`examples/default/`](https://github.com/rsgalloway/envstack/tree/master/examples/default):
  foundational stack examples and derived values
- [`examples/project/`](https://github.com/rsgalloway/envstack/tree/master/examples/project):
  project-oriented stack activation
- [`examples/encryption/`](https://github.com/rsgalloway/envstack/tree/master/examples/encryption):
  encrypted values and key stacks
- [`examples/wrappers/`](https://github.com/rsgalloway/envstack/tree/master/examples/wrappers):
  wrapper stacks and launcher patterns
