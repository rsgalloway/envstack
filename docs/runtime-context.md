# Runtime Context

Runtime context is the information available when a stack is loaded or resolved:
the launching process environment, selected stack names, selected platform,
search directories, and explicitly defined stack values. Modifiers select and
compose those values; YAML tags encode, decode, encrypt, or hash representations.
See [Variable expansion](expansion.md) for their syntax and evaluation order.

## Context and Stack Data

`ROOT`, `ENV`, `HOME`, and `USER` are ordinary variable names. A stack can define
them, use a self-reference to inherit them, or leave them absent so references
can fall back to the process environment. envstack does not inject a complete
runtime-variable dictionary into every loaded stack.

Likewise, `PLATFORM` inside a stack is ordinary data. Selecting `--platform
windows` or `load_environ(..., platform="windows")` chooses YAML sections and
path delimiters; it does not create or overwrite a `PLATFORM` variable. Changing
that variable does not change platform selection.

`STACK` is special: loading supplies the last requested stack name when the
merged stack has no truthy `STACK` value. A nonempty value defined in a stack is
preserved. Treat `STACK` as loader metadata rather than using it for unrelated
application data.

## Runtime Controls

Set import-time controls in the launching shell before starting envstack, or
before importing it in Python. A same-named value inside a stack is still data;
it does not reconfigure constants already read by the running process.

| Name | Purpose and timing |
| --- | --- |
| `ENVPATH` | Search directories, separated by the host's path delimiter. Read when loading; a resolved stack `ENVPATH` can affect subsequent requested stacks. The current directory is also searched. |
| `DEFAULT_NAMESPACE` | Default stack name, read at import time; defaults to `default`. Explicit stack arguments override it. |
| `ALLOW_COMMANDS` | Enable `$(...)`, read at import time; disabled by default. Values `1`, `true`, `True`, and `TRUE` enable it. |
| `COMMAND_TIMEOUT` | Command timeout in seconds, read at import time; defaults to 5, including when the setting is not an integer. |
| `IGNORE_MISSING` | Ignore missing stack files, read at import time; enabled by default. Uses the same true values as `ALLOW_COMMANDS`. The Python loading API can override it. |
| `LOG_LEVEL` | Logging level read at import time; defaults to `INFO`. |
| `INTERACTIVE` | Read from a command wrapper's environment to select interactive command execution. |
| `SHELL` / `ComSpec` | Host shell detection at import time: `SHELL` on POSIX and `ComSpec` on Windows. |
| `ENVSTACK_SHELL` | Override the shell selected when launching an envstack shell session. |
| `ENVSTACK_SYMMETRIC_KEY` | AES-GCM key used during encryption/decryption. |
| `ENVSTACK_FERNET_KEY` | Fernet key used during encryption/decryption. |

Enabling command substitution in a stack with `ALLOW_COMMANDS: 1` does not
enable it for the process currently loading that file. Exporting that value can
influence a subsequently launched envstack process.

## Runtime Names and Collisions

Use application-specific names, such as `MYAPP_CACHE_ROOT`, for application
settings. Keep `ENVSTACK_*` for envstack integration, and avoid repurposing the
runtime control names above. This is naming guidance, not an enforced reserved
namespace: the loader does not reject these keys or emit collision warnings.
There is no separate runtime lookup syntax or implicit `ENVSTACK_*` variable
expansion mechanism.

The current collision behavior is:

- Ordinary references prefer stack definitions over shell values. An explicit
  empty string also wins. A missing variable can fall back to the shell.
- A self-reference uses preceding stack definitions before the shell.
- Import-time control settings and same-named stack data can differ. For example,
  a stack's `LOG_LEVEL` does not automatically reconfigure the current logger.
- For decryption, process-environment encryption keys override matching stack
  keys. Do not use key names for unrelated data.
- A nonempty stack-defined `STACK` overrides the loader's default metadata value.

No new collision rejection or reserved-prefix enforcement is introduced by
this model. Applications should not assume that writing a runtime-looking name
inside a stack changes envstack's own state.

## Inspect Before Applying

```bash
envstack myapp -u ROOT ENV DEPLOY_ROOT
envstack myapp -r ROOT ENV DEPLOY_ROOT
```

The first command displays stored values; the second displays resolved values.
Both load the stack, so enabled commands may run during internal `ENVPATH`
resolution. Neither command changes the invoking shell's environment.

For an application process, use `envstack myapp -- command`, or apply a stack
inside Python with `envstack.init("myapp")`. The [Python API](api.md) describes
loading, resolution, activation, and restoration.
