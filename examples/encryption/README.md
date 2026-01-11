## Encryption

Supported encryption algorithms include
[AES-GCM](https://en.wikipedia.org/wiki/Galois/Counter_Mode),
[Fernet](https://github.com/fernet/spec/),
and
[Base64](https://en.wikipedia.org/wiki/Base64). This allows
you to securely encrypt and decrypt sensitive environment variables.

To use AES-GCM or Fernet, and encryption key must be found somewhere in the
environment. No key is required for Base64 encryption (the default). Encrypted
nodes look for keys in the following order, favoring AES-GCM over Fernet:

| Algorithm | Key |
|---------|-------------|
| Base64 | (no key required) |
| AES-GCM | ${ENVSTACK_SYMMETRIC_KEY} |
| Fernet | ${ENVSTACK_FERNET_KEY} |

If no encryption keys are found in the environment, envstack will default to
using Base64 encoding:

```bash
$ envstack -eu
DEPLOY_ROOT=JHtST09UfS8ke0VOVn0=
ENV=cHJvZA==
ENVPATH=JHtERVBMT1lfUk9PVH0vZW52OiR7RU5WUEFUSH0=
HELLO=JHtIRUxMTzo9d29ybGR9
LOG_LEVEL=JHtMT0dfTEVWRUw6PUlORk99
PATH=JHtERVBMT1lfUk9PVH0vYmluOiR7UEFUSH0=
PYTHONPATH=JHtERVBMT1lfUk9PVH0vbGliL3B5dGhvbjoke1BZVEhPTlBBVEh9
ROOT=L21udC9waXBl
STACK=ZGVmYXVsdA==
```

#### Generating Keys

To use AES-GCM or Fernet encryption and serialize to an `encrypted.env` file,
first generate and source keys in the shell using the `--keygen` option:

```bash
$ source <(envstack --keygen --export)
```

Once the keys are in the environment, you can encrypt the env stack:

```bash
$ envstack -o secrets.env --encrypt
```

Encrypted variables will resolve as long as the key is in the environment:

```bash
$ envstack secrets -r HELLO
HELLO=world
```

#### Storing Keys

Keys can be stored in other environment stacks, e.g. a `keys.env` file
(keys are automatically base64 encoded):

```bash
$ envstack --keygen -o keys.env
```

Then use `keys.env` to encrypt any other environment files:

```bash
$ ./keys.env -- envstack -eo secrets.env
```

To decrypt, run the command inside the `keys` environment again:

```bash
$ ./keys.env -- envstack secrets -r HELLO
HELLO=world
```

Or add `keys` to the env stack:

```bash
$ envstack keys secrets -r HELLO
HELLO=world
```

Or automatically include `keys`:

```yaml
include: [keys]
```

Variables will automatically decrypt when resolved:

```bash
$ ./secrets.env -r HELLO
HELLO=world
```