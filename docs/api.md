# Python API

The Python API mirrors the CLI closely: you can load raw stack files, resolve
them into concrete values, apply them to `os.environ`, and optionally encrypt
or serialize the result.

The examples below use the repository's sample stacks under `examples/` so the
behavior is easier to reason about.

## Loading an environment stack

Loading a stack returns an unresolved `Env` object. Variable references and
modifiers are still present at this stage:

```bash
export ENVPATH=./examples/default
```

```python
>>> import envstack
>>> env = envstack.load_environ("default")
>>> env["ENV"]
'prod'
>>> env["DEPLOY_ROOT"]
'${ROOT}/${ENV}'
>>> env["STACK"]
'default'
```

This is the programmatic equivalent of:

```bash
$ envstack default -u
```

## Resolving a stack into concrete values

To evaluate variable references such as `${ROOT}/${ENV}`, resolve the loaded
environment:

```python
>>> resolved = envstack.resolve_environ(env)
>>> resolved["ENV"]
'prod'
>>> resolved["ROOT"]
'/mnt/pipe'
>>> resolved["DEPLOY_ROOT"]
'/mnt/pipe/prod'
```

This matches the CLI's resolved mode:

```bash
$ envstack default -r
```

## Loading inherited stacks

The `dev` example includes `default`, then overrides a few values:

```python
>>> dev = envstack.resolve_environ(envstack.load_environ("dev"))
>>> dev["ENV"]
'dev'
>>> dev["LOG_LEVEL"]
'DEBUG'
>>> dev["DEPLOY_ROOT"]
'/mnt/pipe/dev'
>>> dev["PATH"].startswith("/mnt/pipe/dev/bin:/mnt/pipe/prod/bin:")
True
```

That pattern is often the most useful API workflow:

```python
>>> resolved = envstack.resolve_environ(envstack.load_environ("dev"))
```

## Initializing `os.environ`

If you want to apply a stack to the current Python process, use `init()`:

```python
>>> import os
>>> envstack.init("dev")
>>> os.getenv("ENV")
'dev'
>>> os.getenv("DEPLOY_ROOT")
'/mnt/pipe/dev'
```

`init()` updates `os.environ` and refreshes `sys.path` from the resolved
`PYTHONPATH`. This makes it useful for bootstrap scripts and embedded tool
launchers.

To restore the prior process environment:

```python
>>> envstack.revert()
>>> os.getenv("ENV") is None
True
```

## Building environments in Python

You can also author an environment directly:

```python
>>> from envstack.env import Env, resolve_environ
>>> env = Env({"FOO": "bar", "BAR": "${FOO}"})
>>> resolve_environ(env)
{'FOO': 'bar', 'BAR': 'bar'}
```

This is useful when generating derived environments before writing them to disk:

```python
>>> env.write("out.env")
```

## Structured values

`envstack` supports lists and dictionaries in stack files. The `data` example
shows how unresolved and resolved values differ:

```python
>>> data_env = envstack.load_environ("data")
>>> data_env["DICT"]
{'a': 1, 'b': 2, 'c': '${INT}'}
>>> resolved = envstack.resolve_environ(data_env)
>>> resolved["DICT"]
{'a': '1', 'b': '2', 'c': '5'}
>>> resolved["CHAR_LIST"]
['a', 'b', 'c', 'world']
```

## Encryption workflow

The `examples/encryption/` stacks provide a concrete encryption example.

Point `ENVPATH` at both example roots:

```python
>>> os.environ["ENVPATH"] = "examples/default:examples/encryption"
```

Load the `keys` stack first so the decryption keys are present in the process
environment:

```python
>>> keys = envstack.resolve_environ(envstack.load_environ("keys"))
>>> os.environ.update({k: str(v) for k, v in keys.items()})
```

Now encrypted values from `secrets.env` will resolve automatically:

```python
>>> secrets = envstack.resolve_environ(envstack.load_environ("secrets"))
>>> secrets["KEY"]
'This is encrypted'
>>> secrets["SECRET"]
'my_super_secret_password'
>>> secrets["PASSWORD"]
'password'
```

You can also encrypt a plain environment in memory:

```python
>>> from envstack.env import Env, encrypt_environ
>>> plain = Env({"SECRET": "super_secret", "PASSWORD": "my_password"})
>>> encrypted = encrypt_environ(plain)
>>> type(encrypted["SECRET"]).__name__
'EncryptedNode'
```

## Common patterns

Load raw stack data:

```python
>>> env = envstack.load_environ("default")
```

Load and resolve in one step:

```python
>>> resolved = envstack.resolve_environ(envstack.load_environ("dev"))
```

Apply a stack to the current process:

```python
>>> envstack.init("dev")
```

Restore the previous process environment:

```python
>>> envstack.revert()
```

## Configuration variables

The following environment variables affect runtime behavior:

| Name | Description |
|------|-------------|
| `ALLOW_COMMANDS` | Allow embedded commands |
| `COMMAND_TIMEOUT` | Embedded command timeout in seconds |
| `DEFAULT_NAMESPACE` | Name of the default environment stack (`default`) |
| `ENVPATH` | Colon-separated paths to search for environment files |
| `IGNORE_MISSING` | Ignore missing stack files when resolving environments |
| `INTERACTIVE` | Force shells to run in interactive mode |
| `STACK` | Stores the name of the current environment stack |
