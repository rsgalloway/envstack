# Accumulating Paths Across Includes

The stacks in [`examples/inheritance/`](https://github.com/rsgalloway/envstack/tree/master/examples/inheritance) model two
Python tools deployed to a shared location. Each tool adds its own platform
folder to `PYTHONPATH`; the application includes both tools and adds its own
Python folder. The paths are illustrative and do not need to exist to run this
example.

The source order is `default`, `toola`, `toolb`, then `app`. Both tools include
`default`, but the shared base is loaded only once.

- `default.env` prepends `${ROOT}/lib/python` to the shell's `PYTHONPATH`.
- `toola.env` appends `${TOOLA_ROOT}/linux`, `/darwin`, or `/windows`.
- `toolb.env` appends the corresponding `${TOOLB_ROOT}` folder.
- `app.env` appends `${ROOT}/app/python`.

## Run the Example

With envstack installed, run these commands in Bash from the repository root:

```bash
cd examples/inheritance
ENVPATH="$PWD" ROOT=/shared PYTHONPATH=ORIG envstack app -r PYTHONPATH
```

On Linux, the resolved value is:

```text
/shared/lib/python:ORIG:/shared/tools/toola/linux:/shared/tools/toolb/linux:/shared/app/python
```

On macOS or Windows, the tool directories use `darwin` or `windows` instead.
The Bash commands above also work in a Bash shell on those platforms.

Load the tools directly to see the same accumulation without the app folder:

```bash
ENVPATH="$PWD" ROOT=/shared PYTHONPATH=ORIG envstack toola toolb -r PYTHONPATH
```

On Linux:

```text
/shared/lib/python:ORIG:/shared/tools/toola/linux:/shared/tools/toolb/linux
```

An empty shell value omits `ORIG`:

```bash
ENVPATH="$PWD" ROOT=/shared PYTHONPATH= envstack app -r PYTHONPATH
```

On Linux:

```text
/shared/lib/python:/shared/tools/toola/linux:/shared/tools/toolb/linux:/shared/app/python
```

To use a different deployment location, change `ROOT`. To override one tool's
location, set `TOOLA_ROOT` or `TOOLB_ROOT`; their defaults use `${ROOT}/tools`.

Each self-reference uses the value accumulated from earlier sources. A literal
assignment such as `PYTHONPATH: /replacement` would reset that value.
See [Variable Expansion](../expansion.md#self-references-across-includes) for
the resolution rules.
