## Python API

To initialize the environment stack in Python, use the `init` function:

```python
>>> envstack.init()
>>> os.getenv("HELLO")
'world'
```

To initialize the "dev" stack:

```python
>>> envstack.init("dev")
>>> os.getenv("ENV")
'dev'
```

To revert the original environment:

```python
>>> envstack.revert()
>>> os.getenv("HELLO")
>>> 
```

Creating and resolving environments:

```python
>>> from envstack.env import Env, resolve_environ
>>> env = Env({"BAR": "${FOO}", "FOO": "foo"})
>>> resolve_environ(env)
{'BAR': 'foo', 'FOO': 'foo'}
```

Create an encrypted environment:

```python
>>> from envstack.env import Env, encrypt_environ
>>> env = Env({"SECRET": "super_secret", "PASSWORD": "my_password"})
>>> encrypted = encrypt_environ(env)
```

Loading and resolving predefined environments from stack files:

```python
>>> from envstack.env import load_environ, resolve_environ
>>> env = load_environ(name)
>>> resolved = resolve_environ(env)
```

## Config

The following environment variables are used to help manage functionality:

| Name | Description |
|------|-------------|
| DEFAULT_ENV_STACK | Name of the default environment stack (default) |
| ENVPATH | Colon-separated paths to search for environment files |
| IGNORE_MISSING | Ignore missing stack files when resolving environments |
| INTERACTIVE | Force shells to run in interactive mode |
| STACK | Stores the name of the current environment stack |
