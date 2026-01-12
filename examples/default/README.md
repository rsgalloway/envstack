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

See the unresolved environment variable values for the `default.env` environment:

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

Running `envstack` will launch a new shell session with the resolved environment:

```shell
$ envstack
🚀 Launching envstack shell... (CTRL+D or "exit" to quit)
(prod) ~$ echo $ROOT
/mnt/pipe
```

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
including `PYTHONPATH`, and `PATH`. Here, we explicitly give dev paths precedence
over prod paths:

```shell
$ envstack dev
🚀 Launching envstack shell... (CTRL+D or "exit" to quit)
(dev) $ echo $PATH
/mnt/pipe/dev/bin:/mnt/pipe/prod/bin:
```

## Storing Data Types

You can store complex data types in envstack, including `dict` and `list` types.
Values can be other `VARS`, for example:

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
environments using Python:

```python
>>> import envstack
>>> env = envstack.load_environ("data")
>>> env.get("DICT")
{'a': 1, 'b': 2, 'c': '${INT}'}
>>> resolved = envstack.resolve_environ(env)
>>> resolved.get("DICT")
{'a': '1', 'b': '2', 'c': '5'}
```
