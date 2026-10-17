# Tools and Inheritance

The stacks in [`examples/tools/`](https://github.com/rsgalloway/envstack/tree/master/examples/tools)
show how an application combines shared Python code with separately deployed
NumPy, Pillow, and OpenEXR builds. Each tool contributes its own import path; the
application includes all three tools without repeating their deployment paths.

## Use Case

NumPy provides arrays for image data, Pillow supports image loading and
processing, and OpenEXR supports EXR image workflows. An application may need
`import numpy`, `from PIL import Image`, and `import OpenEXR`, while their
native builds are deployed separately from shared Python code.

Each package has a versioned tool root with platform-specific **`lib/python`**
directories. Its env file includes `default` and appends the appropriate import
path. The `tools` stack includes all three packages, demonstrating why those
self-references must accumulate.

## Deployment Layout

```text
/shared/prod/
  lib/python/                          # shared Python code
  bin/                                 # shared launchers
  tools/
    numpy/2.2.6/windows/python3.11/
      lib/python/
        numpy/
        numpy.libs/                    # bundled native libraries
    numpy/2.2.6/windows/python3.12/
      lib/python/
        numpy/
        numpy.libs/
    pillow/12.3.0/windows/
      lib/python/
        PIL/
          _imaging.cp311-win_amd64.pyd
      bin/                             # optional separately deployed DLLs/tools
    openexr/3.4.13/windows/
      lib/python/
        Imath.py
        OpenEXR.cp311-win_amd64.pyd
      bin/                             # optional separately deployed DLLs/tools
  apps/tools/lib/python/
```

The tree illustrates Windows builds, including two NumPy runtimes. Download wheels compatible
with the consuming interpreter and architecture, preserving bundled libraries
and package-relative paths. Use separate deployment roots or runtime directories
when complete package trees for different interpreters would conflict.
NumPy has a complete package tree for each runtime. Its stack adds a
`python${PYVERSION}` directory before `lib/python` to keep these trees
separate. It evaluates the runtime version when the stack is resolved:

```yaml
PYVERSION: $(python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")
```

Deploy a matrix of runtime builds, then put the intended `python` on `PATH`
(for example, activate its virtual environment) before resolving the stack.
A Python 3.11 launch selects `python3.11/lib/python`; Python 3.12 selects
`python3.12/lib/python` under the same package-version/platform root.
Set `ALLOW_COMMANDS=1` before starting envstack to enable command substitution.
This selects from already deployed builds; it does not install a missing build.

OpenEXR includes the NumPy stack so its dependency is available even when
loading `openexr` directly.

## How the Includes Accumulate

`tools.env` contains:

```yaml
include: [numpy, pillow, openexr]
all:
  PYTHONPATH: ${PYTHONPATH}:${DEPLOY_ROOT}/apps/tools/lib/python
```

All three tools include `default`; OpenEXR also includes `numpy`. Shared
includes load once, giving this order:

```text
default → numpy → pillow → openexr → tools
```

The shared base loads once. It prepends `${DEPLOY_ROOT}/lib/python` to the
shell's `PYTHONPATH`. NumPy, Pillow, and OpenEXR append their selected
`lib/python` directory, then the app appends its own directory. On Windows,
Pillow and OpenEXR also append their native `bin` directories to `PATH`.

A self-reference uses the value accumulated so far. A literal assignment such
as `PYTHONPATH: /replacement` resets it. The same rules apply to `PATH` and
custom search variables.

## Run the Example

From the repository root, run this one-line check:

```bash
ALLOW_COMMANDS=1 ENVPATH=./examples/tools/ envstack tools -r PYTHONPATH
```

For example, on Linux with Python 3.12 and `PYTHONPATH=/existing/python`:

```text
PYTHONPATH=/shared/prod/lib/python:/existing/python:/shared/prod/tools/numpy/2.2.6/linux/python3.12/lib/python:/shared/prod/tools/pillow/12.3.0/linux/lib/python:/shared/prod/tools/openexr/3.4.13/linux/lib/python:/shared/prod/apps/tools/lib/python
```

The output retains the shell's existing `PYTHONPATH` and selects the NumPy
runtime directory using `python` on `PATH`. No deployed files are needed to
inspect these paths.

The current directory is always searched, so no `ENVPATH` setting is needed
after changing into `examples/tools`. Set the shell values explicitly for a
predictable comparison:

```bash
cd examples/tools
ROOT=/shared ALLOW_COMMANDS=1 PYTHONPATH=ORIG envstack tools -r PYTHONPATH
```

On Linux with Python 3.11 on `PATH`:

```text
PYTHONPATH=/shared/prod/lib/python:ORIG:/shared/prod/tools/numpy/2.2.6/linux/python3.11/lib/python:/shared/prod/tools/pillow/12.3.0/linux/lib/python:/shared/prod/tools/openexr/3.4.13/linux/lib/python:/shared/prod/apps/tools/lib/python
```

Load the tools directly to omit the app's Python directory:

```bash
ROOT=/shared ALLOW_COMMANDS=1 PYTHONPATH=ORIG envstack numpy pillow openexr -r PYTHONPATH
```

Set `PYTHONPATH=` to omit `ORIG`. Set `ROOT` to your deployment share, or set
`NUMPY_VERSION`, `PILLOW_VERSION`, and `OPENEXR_VERSION` to other deployed
package versions. `NUMPY_ROOT`, `PILLOW_ROOT`, and `OPENEXR_ROOT` override
the entire versioned tool root; the
platform and `lib/python` suffixes still come from the tool stack, along with
the runtime directory for NumPy.

## Download, Install, and Try the Libraries

From the directory containing the example stack files, use `pip install
--target` to download and install each package into its deployed location.
These Bash commands select builds for the active `python`:

```bash
export ROOT="$(python -c "import tempfile; print(tempfile.mkdtemp(prefix='envstack-tools-'))")"
export ALLOW_COMMANDS=1
tool_platform=$(python -c "import platform; print(platform.system().lower())")
python_version=$(python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")

python -m pip install --only-binary=:all: --no-deps \
  --target "$ROOT/prod/tools/numpy/2.2.6/$tool_platform/python$python_version/lib/python" \
  numpy==2.2.6
python -m pip install --only-binary=:all: --no-deps \
  --target "$ROOT/prod/tools/pillow/12.3.0/$tool_platform/lib/python" \
  Pillow==12.3.0
python -m pip install --only-binary=:all: --no-deps \
  --target "$ROOT/prod/tools/openexr/3.4.13/$tool_platform/lib/python" \
  OpenEXR==3.4.13
```

`--target` selects the install directory; `--no-deps` prevents pip from
installing a second NumPy copy under the OpenEXR directory. NumPy is installed
explicitly in its own directory. See the
[pip install reference](https://pip.pypa.io/en/stable/cli/pip_install/),
[Pillow installation guide](https://pillow.readthedocs.io/en/stable/installation/index.html),
and [OpenEXR Python guide](https://openexr.com/en/latest/python.html).

Check that the stack exposes all three libraries:

```bash
envstack tools -- python -c "import numpy; from PIL import Image; import OpenEXR; print(numpy.__file__); print(Image.__file__); print(OpenEXR.__file__)"
```

The printed module paths should point into the three deployed tool directories.
Use a fresh deployment root when trying a different interpreter or architecture;
these commands install one runtime's package payload. If no compatible binary
wheel exists for a pin, pip reports an error. The optional Windows `bin`
directories are not created here; each wheel retains its bundled library layout.

### Optional: Automate the Setup with Python

As a convenience, the following script performs the same installation and import
checks. Run it in a fresh Python process from the directory containing the
example stack files (`tools.env`, `default.env`, `numpy.env`, `pillow.env`, and
`openexr.env`). It creates a fresh temporary deployment directory:

```python
import os
import platform
from pathlib import Path
import subprocess
import sys
import tempfile

# Enable substitution before importing envstack and use this interpreter's bin directory.
os.environ["ALLOW_COMMANDS"] = "1"
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")

import envstack

root = Path(tempfile.mkdtemp(prefix="envstack-tools-"))
platform_name = platform.system().lower()
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
packages = {
    "numpy": ("numpy", "2.2.6"),
    "pillow": ("Pillow", "12.3.0"),
    "openexr": ("OpenEXR", "3.4.13"),
}

os.environ["ROOT"] = str(root)
for tool, (package, version) in packages.items():
    tool_root = root / "prod" / "tools" / tool / version
    build_root = tool_root / platform_name
    if tool == "numpy":
        build_root /= f"python{python_version}"
    target = build_root / "lib" / "python"
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "--only-binary=:all:", "--no-deps",
            "--target", str(target), f"{package}=={version}",
        ],
        check=True,
    )
    os.environ[f"{tool.upper()}_VERSION"] = version
    os.environ[f"{tool.upper()}_ROOT"] = str(tool_root)

envstack.init("tools")

import numpy as np
from PIL import Image
import OpenEXR

image = Image.new("RGB", (64, 64), "red")
print("NumPy:", np.__file__, np.asarray(image).shape)
print("Pillow:", Image.__file__, image.size)
print("OpenEXR:", OpenEXR.__file__)
print("PYTHONPATH:", os.environ["PYTHONPATH"])
```

### Download for Another Platform

To download for another platform without installing locally, use pip's target
options. For example, download Windows x86-64 CPython 3.11 wheels:

```bash
python -m pip download --only-binary=:all: --no-deps --platform win_amd64 --python-version 311 --implementation cp --abi cp311 --dest wheels/windows-cp311 numpy==2.2.6 Pillow==12.3.0 OpenEXR==3.4.13
```

On the matching target machine, the install commands or optional script can
use those files by adding `--no-index` and `--find-links wheels/windows-cp311` to the pip
arguments. Downloading a Windows wheel does not make it importable on Linux
or macOS. See
[pip download](https://pip.pypa.io/en/stable/cli/pip_download/) for the target
selection options.

## Stage and Deploy with distman

[`dist.json`](https://github.com/rsgalloway/envstack/blob/master/examples/tools/dist.json)
maps local build artifacts to the paths used by these stacks.
[distman](https://distman.dev) deploys the files; envstack selects their runtime
paths. The direct `pip --target` commands above install at the final location.
For distribution to a shared location, install into `staging/` first instead.

From the directory containing the example stacks and `dist.json`:

```bash
tool_platform=$(python -c "import platform; print(platform.system().lower())")
python_version=$(python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")

python -m pip install --only-binary=:all: --no-deps \
  --target "staging/numpy/2.2.6/$tool_platform/python$python_version/lib/python" \
  numpy==2.2.6
python -m pip install --only-binary=:all: --no-deps \
  --target "staging/pillow/12.3.0/$tool_platform/lib/python" \
  Pillow==12.3.0
python -m pip install --only-binary=:all: --no-deps \
  --target "staging/openexr/3.4.13/$tool_platform/lib/python" \
  OpenEXR==3.4.13
```

Repeat the NumPy staging step with each supported interpreter to populate its
runtime directories. Stage other platforms on matching build hosts or install
wheels selected for those targets. Preserve the complete `lib/python` payload,
including bundled native libraries. Any separately managed `bin` directory
belongs beside `lib` under the corresponding platform directory.

The manifest uses these mappings:

| Target | Local source | Destination |
| --- | --- | --- |
| `env` | `*.env` | `{DEPLOY_ROOT}/env/%1.env` |
| `numpy` | `staging/numpy/2.2.6/*/*` | `{DEPLOY_ROOT}/tools/numpy/2.2.6/%1/%2` |
| `pillow` | `staging/pillow/12.3.0/*` | `{DEPLOY_ROOT}/tools/pillow/12.3.0/%1` |
| `openexr` | `staging/openexr/3.4.13/*` | `{DEPLOY_ROOT}/tools/openexr/3.4.13/%1` |

Each `*` captures one path component, substituted as `%1`, then `%2`.
For example, NumPy's `linux/python3.11` source directory maps to the same
platform/runtime suffix at the destination. The nested `lib/python` is copied
with that directory. Package versions in the manifest and env files must match;
update both when changing a pin.

Preview and deploy the staged builds and env files:

```bash
export ROOT=/shared
export DEPLOY_ROOT="$ROOT/prod"
dist --all --dryrun -t env numpy pillow openexr
dist --all -t env numpy pillow openexr
```

`--all` includes ignored build artifacts and hidden package files. The manifest
uses content matching so changes to staged artifacts produce new deployment
versions. `DEPLOY_ROOT` is explicit here because distman runs independently of
the env stack; it must match the `${ROOT}/prod` layout in `default.env`.

After deployment, select the installed env files:

```bash
ALLOW_COMMANDS=1 ENVPATH="$DEPLOY_ROOT/env" envstack tools -r PYTHONPATH
```

For a separate GUI deployment, see the [PySide6 example](pyside.md).

## Windows PATH and DLLs

In PowerShell, from the repository root:

```powershell
Set-Location examples/tools
$env:ROOT = '//server/pipeline'
$env:ALLOW_COMMANDS = '1'
envstack tools -r PYTHONPATH PATH
```

On Windows, search paths use semicolons. All three package import directories appear
in `PYTHONPATH`. The `PATH` value contains:

```text
//server/pipeline/prod/bin;<inherited PATH>;//server/pipeline/prod/tools/pillow/12.3.0/windows/bin;//server/pipeline/prod/tools/openexr/3.4.13/windows/bin
```

These `bin` entries demonstrate deployments with separate DLLs or native tools.
Neither package should be assumed to require an extra `bin` directory when
its wheel already bundles dependencies.
Point `PATH` at the actual native directories your deployment provides.

For Python 3.8+, `PATH` alone does not cover every extension-module dependency.
If dependencies live outside the package's loader-managed locations, register
them in the Python process using
[`os.add_dll_directory()`](https://docs.python.org/3/library/os.html#os.add_dll_directory)
before importing the extension. For a deployment with these separate DLL
directories, after activating the stack:

```python
import os

# Keep the handles alive while the application uses the native libraries.
dll_directories = []
if os.name == "nt":
    for name in ("PILLOW_ROOT", "OPENEXR_ROOT"):
        directory = os.path.join(os.environ[name], "windows", "bin")
        dll_directories.append(os.add_dll_directory(directory))
```

Envstack composes paths; it does not fetch wheels, verify binary compatibility,
or register DLL directories inside the application. Package loaders may already
handle their bundled libraries.

See [Variable Expansion](../expansion.md#self-references-across-includes) for
the resolution rules.
