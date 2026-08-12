# Default Example

Start by downloading some example files:

```shell
curl -o \
default.env \
https://raw.githubusercontent.com/rsgalloway/envstack/master/examples/default/default.env
```
```shell
curl -o \
dev.env \
https://raw.githubusercontent.com/rsgalloway/envstack/master/examples/default/dev.env
```
```shell
curl -o \
data.env \
https://raw.githubusercontent.com/rsgalloway/envstack/master/examples/default/data.env
```

See the unresolved environment variable values for the `default.env`
environment:

```shell
$ envstack -u
DEPLOY_ROOT=${ROOT}/${ENV}
ENV=prod
ENVPATH=${DEPLOY_ROOT}/env:${ENVPATH}
LOG_LEVEL=${LOG_LEVEL:=INFO}
PATH=${DEPLOY_ROOT}/bin:${PATH}
PS1=\[\e[32m\](${ENV})\[\e[0m\] \w\$ 
PYTHONPATH=${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
ROOT=/mnt/pipe
STACK=default
```

Running `envstack` launches a new shell session with the resolved environment:

```shell
$ envstack
🚀 Launching envstack shell... (CTRL+D or "exit" to quit)
(prod) ~$ echo $ROOT
/mnt/pipe
```

## Includes

Environment stack files can include other namespaced environments:

```yaml
include: [default, test]
```

In practice, most derived stacks should include `default`.

## Loading Environments With Inheritance

Load the `dev.env` environment's unresolved values:

```shell
$ envstack dev -u
DEPLOY_ROOT=${ROOT}/dev
ENV=dev
ENVPATH=${ROOT}/dev/env:${ROOT}/prod/env:${ENVPATH}
LOG_LEVEL=DEBUG
PATH=${ROOT}/dev/bin:${ROOT}/prod/bin:${PATH}
PS1=\[\e[32m\](${ENV})\[\e[0m\] \w\$ 
PYTHONPATH=${ROOT}/dev/lib/python:${ROOT}/prod/lib/python:${PYTHONPATH}
ROOT=/mnt/pipe
STACK=dev
```

Note how `ROOT` is undefined in `dev.env`, and inherited from `default.env`.
The `dev.env` environment also overrides some of the values in `default.env`,
including `PYTHONPATH` and `PATH`. Here, dev paths take precedence over prod
paths:

```shell
$ envstack dev
🚀 Launching envstack shell... (CTRL+D or "exit" to quit)
(dev) $ echo $PATH
/mnt/pipe/dev/bin:/mnt/pipe/prod/bin:
```

## Storing Data Types

You can store complex data types in envstack, including `dict` and `list`
types. Values can themselves reference other vars:

```shell
$ envstack data -u
CHAR_LIST=['a', 'b', 'c', '${HELLO}']
DICT={'a': 1, 'b': 2, 'c': '${INT}'}
FLOAT=1.0
HELLO=world
INT=5
LOG_LEVEL=${LOG_LEVEL:=INFO}
NUMBER_LIST=[1, 2, 3]
STACK=data
```
```shell
$ envstack data -r CHAR_LIST
CHAR_LIST=['a', 'b', 'c', 'world']
```

Data types are also automatically converted using `safe_eval` when loading
environments in Python:

```python
>>> import envstack
>>> env = envstack.load_environ("data")
>>> env.get("DICT")
{'a': 1, 'b': 2, 'c': '${INT}'}
>>> resolved = envstack.resolve_environ(env)
>>> resolved.get("DICT")
{'a': '1', 'b': '2', 'c': '5'}
```

## Executing Environments

envstack files are scripts that can be executed:

```bash
$ envstack test -s FOO=bar -o test.env
$ ./test.env -- echo {FOO}
bar
```

Or exported:

```bash
$ ./test.env --export
export FOO=bar
export STACK=test
```

## Command Substitution and Derived Values

The `test.env` example shows how a stack can derive a value from a command at
resolution time:

```yaml
PYVERSION: $(python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")
PYTHONPATH: ${DEPLOY_ROOT}/lib/python${PYVERSION}
NUKESCRIPT: ${ROOT}/projects/{seq}/{shot}/comp/{show}_{seq}_{shot}.{version}.nk
```

This is useful when a path or tool setting depends on the local runtime. For
example, `PYTHONPATH` can follow the active interpreter's major/minor version
without hard-coding it into every stack file.

To inspect it:

```bash
$ envstack test -u
PYVERSION=$(python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")
PYTHONPATH=${DEPLOY_ROOT}/lib/python${PYVERSION}
NUKESCRIPT=${ROOT}/projects/{seq}/{shot}/comp/{show}_{seq}_{shot}.{version}.nk
```

```bash
$ envstack test -r PYVERSION
```

That returns the major/minor interpreter version detected on the local
machine, and `PYTHONPATH` resolves using that value.

## More Details

Variables can be platform specific:

```yaml
darwin:
  HELLO: olleh
linux:
  HELLO: world
windows:
  HELLO: goodbye
```

Variables can reference other variables:

```yaml
all: &all
  FOO: ${BAR}
  BAR: ${BAZ}
  BAZ: ${BIZ}
  BIZ: ${BIZ:=foo}
```

As you might expect, the above resolves to:

```bash
$ envstack -r
BAR=foo
BAZ=foo
BIZ=foo
FOO=foo
```

Here is an example using nested variable expansion:

```yaml
FOO: ${BIZ:=${BAR:=${BAZ:=baz}}}
```

Resolves to:

```bash
$ envstack -r
FOO=baz
```
