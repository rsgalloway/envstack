# Secrets and Encryption

envstack supports **optional encryption of environment values** to protect
sensitive data when environment files are written to disk, checked into version
control, or distributed as artifacts.

Encryption in envstack is designed to protect **values at rest**, not to act as a
full secret management system.

If a value is present in the process environment, it is treated as data.

---

## What encryption in envstack does (and does not)

### envstack encryption **does**
- Protect environment values when serialized to files
- Allow encrypted values to be committed or shared safely
- Decrypt values automatically at resolution time
- Integrate cleanly with environment stacks and includes

### envstack encryption **does not**
- Hide secrets from the running process
- Prevent subprocess inheritance
- Manage key rotation, access control, or auditing
- Replace dedicated secret managers (Vault, KMS, SOPS, etc.)

envstack assumes that **if a key is present in the environment, it is allowed to
decrypt values**.

---

## Supported encryption algorithms

envstack supports the following encryption algorithms:

| Algorithm | Key required | Environment variable |
|---------|--------------|----------------------|
| Base64  | No           | (default)            |
| AES-GCM | Yes          | `ENVSTACK_SYMMETRIC_KEY` |
| Fernet  | Yes          | `ENVSTACK_FERNET_KEY` |

Resolution prefers stronger algorithms when keys are available:

1. AES-GCM
2. Fernet
3. Base64 (fallback)

If no encryption keys are found in the environment, envstack defaults to Base64.

---

## Encrypting environment values

To encrypt the resolved environment:

```bash
$ envstack --encrypt
```

Example output (Base64 fallback):

```env
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

---

## Generating encryption keys

To use AES-GCM or Fernet, keys must exist in the environment.

Generate keys with:

```bash
$ source <(envstack --keygen --export)
```

On Windows (CMD):

```bat
> envstack --keygen > keys.bat
> call keys.bat
```

Once keys are present, encrypted output will use the strongest available
algorithm automatically.

---

## Writing encrypted environment files

```bash
$ envstack --encrypt -o encrypted.env
```

Encrypted values will resolve correctly as long as the appropriate key is present:

```bash
$ envstack encrypted -r HELLO
HELLO=world
```

---

## Storing keys in environment stacks

Keys may be stored in a dedicated environment stack (e.g. `keys.env`).

Generate and store keys:

```bash
$ envstack --keygen -o keys.env
```

Use the keys stack to encrypt another stack:

```bash
$ envstack keys -- envstack --encrypt -o encrypted.env
```

To decrypt, include the keys stack:

```bash
$ envstack keys encrypted -r HELLO
HELLO=world
```

Or declare it as an include:

```yaml
include: [keys]
```

Values will automatically decrypt during resolution.

---

## Recommended usage patterns

- Encrypt environment files before committing or distributing
- Keep keys out of version control
- Use includes to inject keys at activation time
- Combine with external secret managers for higher security needs

envstack encryption is intentionally simple, explicit, and inspectable.