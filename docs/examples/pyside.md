# PySide6

The [`examples/pyside/`](https://github.com/rsgalloway/envstack/tree/master/examples/pyside)
stack selects a versioned, platform-specific PySide6 installation for a GUI
application. It can be used independently of the [imaging tools example](tools.md).

`pyside6.env` includes `default` and appends the selected tool directory to
`PYTHONPATH`:

```text
${DEPLOY_ROOT}/tools/pyside6/${PYSIDE6_VERSION}/<platform>/lib/python
```

The default version is `6.8.3`. Set `PYSIDE6_VERSION` to another deployed version,
or override `PYSIDE6_ROOT` to select a different versioned tool root.

## Install and Run

From the directory containing `default.env`, `pyside6.env`, and `hello.py`,
install the build for the active interpreter and platform:

```bash
export ROOT="$(python -c "import tempfile; print(tempfile.mkdtemp(prefix='envstack-pyside-'))")"
tool_platform=$(python -c "import platform; print(platform.system().lower())")

python -m pip install --only-binary=:all: \
  --target "$ROOT/prod/tools/pyside6/6.8.3/$tool_platform/lib/python" \
  PySide6==6.8.3
```

Let pip install PySide6's dependencies into the same target directory:
`PySide6_Essentials`, `PySide6_Addons`, and `shiboken6`. The dependencies
supply the bindings and Qt binaries; installing the top-level package with
`--no-deps` would leave an incomplete installation.
See [Qt's package details](https://doc.qt.io/qtforpython-6.8/package_details.html).

Keep the installed directory tree intact, including Qt's plugins and libraries.
The wheels configure their bundled Qt paths; this stack only adds their Python
import directory. Custom Qt/plugin deployments may need additional settings,
but ordinary wheel installs should use their own bundled layout.

Check the selected path and Qt version:

```bash
envstack pyside6 -r PYTHONPATH
envstack pyside6 -- python -c "from PySide6.QtCore import qVersion; print(qVersion())"
```

Launch the example window:

```bash
envstack pyside6 -- python hello.py
```

`hello.py` creates a `QApplication`, displays a label, and starts Qt's event
loop. Run it in a desktop session with the system libraries required by Qt.

For a path-only check from the envstack repository root:

```bash
ENVPATH=./examples/pyside/ envstack pyside6 -r PYTHONPATH
```

## Stage and Deploy with distman

[`dist.json`](https://github.com/rsgalloway/envstack/blob/master/examples/pyside/dist.json)
keeps the distribution destinations aligned with `pyside6.env`. To prepare a
shared deployment, install into `staging/` instead of the final location:

```bash
tool_platform=$(python -c "import platform; print(platform.system().lower())")
python -m pip install --only-binary=:all: \
  --target "staging/pyside6/6.8.3/$tool_platform/lib/python" \
  PySide6==6.8.3
```

The manifest maps each staged platform directory to its deployed counterpart:

```json
{
  "source": "staging/pyside6/6.8.3/*",
  "destination": "{DEPLOY_ROOT}/tools/pyside6/6.8.3/%1"
}
```

The `*` captures `linux`, `darwin`, or `windows`; `%1` preserves that component
at the destination. The complete `lib/python` tree is copied beneath it.
Stage builds for other platforms separately. Keep the version in `dist.json`,
`pyside6.env`, and the pip commands aligned when changing the package pin.

The `env` target deploys `default.env` and `pyside6.env` to
`{DEPLOY_ROOT}/env/`. The `hello` target deploys the script to
`{DEPLOY_ROOT}/apps/pyside/hello.py`. Preview and deploy with
[distman](https://distman.dev):

```bash
export ROOT=/shared
export DEPLOY_ROOT="$ROOT/prod"
dist --all --dryrun -t env pyside6 hello
dist --all -t env pyside6 hello
```

`--all` includes ignored build artifacts and hidden package files. The manifest
uses content matching for staged artifacts. Set `DEPLOY_ROOT` to the same
`${ROOT}/prod` location used by the env stack.

Launch the deployed script:

```bash
ENVPATH="$DEPLOY_ROOT/env" envstack pyside6 -- python "$DEPLOY_ROOT/apps/pyside/hello.py"
```

The imaging and PySide6 examples share the same base `default.env`, so their
`env` targets can deploy into the same directory. Once both sets of builds and
stacks are deployed, combine them for a GUI that uses the imaging libraries:

```bash
ALLOW_COMMANDS=1 ENVPATH="$DEPLOY_ROOT/env" envstack tools pyside6 -r PYTHONPATH
```
