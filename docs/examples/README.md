# Examples

The example stacks under `examples/` are now documented here as first-class
guides for the canonical docs site.

Start with the default example, then branch into project activation,
encryption, or wrappers depending on the workflow you need.

## Guides

- [Default example](default.md): base stacks, inheritance, structured values,
  executable stacks, and command substitution with `test.env`
- [Tools and inheritance](tools.md): NumPy, Pillow, and OpenEXR deployment patterns,
  shared includes, and accumulation of Python and Windows DLL search paths
- [PySide6](pyside.md): shared Qt Python builds, a small GUI, and distman deployment
- [Project example](project.md): project-scoped path layouts driven by the
  active stack name
- [Encryption example](encryption.md): key generation, encrypted nodes, and
  decryptable values in versioned stack files
- [Wrappers](wrappers.md): launcher scripts that always run a command inside a
  known stack, including the `bin/hello` example

## Repository Layout

- [`examples/default/`](https://github.com/rsgalloway/envstack/tree/master/examples/default):
  foundational stack examples and derived values
- [`examples/tools/`](https://github.com/rsgalloway/envstack/tree/master/examples/tools):
  versioned, platform-specific tools composed through shared includes
- [`examples/pyside/`](https://github.com/rsgalloway/envstack/tree/master/examples/pyside):
  a standalone PySide6 stack and matching distribution manifest
- [`examples/project/`](https://github.com/rsgalloway/envstack/tree/master/examples/project):
  project-oriented stack activation
- [`examples/encryption/`](https://github.com/rsgalloway/envstack/tree/master/examples/encryption):
  encrypted values and key stacks
- [`examples/wrappers/`](https://github.com/rsgalloway/envstack/tree/master/examples/wrappers):
  wrapper stacks and launcher patterns
