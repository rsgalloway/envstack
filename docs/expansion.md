# Variable Expansion

Runtime variables provide context. Parameter modifiers select and compose
values. YAML tags transform their representation when values are resolved or
written. These mechanisms work together, but they run at different stages.

For example, a shell-supplied `ROOT` provides context, `${ROOT:-/shared}` selects
a fallback, and `!base64` marks a stored encoded value for decoding. A tag does
not change variable precedence or select the active stack.

See [Runtime context](runtime-context.md) for control variables and name collisions.

envstack supports Bash-like variable expansion inside stack values.

This is the syntax behind values such as `${ROOT}/${ENV}`,
`${LOG_LEVEL:=INFO}`, and nested defaults like `${VAR:=${FOO:=bar}}`.

## Supported forms

| Form | Meaning |
|------|---------|
| `${VAR}` | Use `VAR`, or an empty string if it is unset |
| `${VAR:=default}` | If `VAR` is unset or empty, use `default` and assign it during resolution |
| `${VAR:-default}` | If `VAR` is unset or empty, use `default` without assigning it |
| `${VAR:?message}` | Raise an error if `VAR` is unset or empty |

This is the complete supported modifier set. Bash forms such as `${VAR-default}`,
`${VAR:+alternate}`, `${#VAR}`, substring operations, and pattern replacements
are not supported. Use the forms above rather than relying on unsupported
expressions to behave like a shell.

These rules apply both in stack files and when resolving values through the
Python API.

## Simple substitution

Direct references use the final stack definition. A missing variable can fall
back to the process environment; an explicit empty string does not:

```yaml
ROOT: /mnt/pipe
ENV: prod
DEPLOY_ROOT: ${ROOT}/${ENV}
```

Resolved output:

```bash
DEPLOY_ROOT=/mnt/pipe/prod
```

If a variable is unset and no modifier is used, envstack resolves it to an
empty string:

```yaml
OPTIONAL_SUFFIX: ${SUFFIX}
```

## Defaults With `:=`

Use `:=` when subsequent references should be able to reuse a fallback. A
self-assignment stays local to the definition being evaluated:

```yaml
LOG_LEVEL: ${LOG_LEVEL:=INFO}
```

If `LOG_LEVEL` is unset or empty, envstack resolves it as `INFO`.

This is especially useful when later values depend on the same variable:

```yaml
ENV: ${ENV:=prod}
ROOT: ${ROOT:=/mnt/pipe}
DEPLOY_ROOT: ${ROOT}/${ENV}
```

## Defaults Without Assignment With `:-`

Use `:-` when you want a fallback in one expression without changing the
variable itself:

```yaml
PROMPT_COLOR: ${PROMPT_COLOR:-green}
```

Here `PROMPT_COLOR` itself resolves to `green` when no preceding value exists.
For a fallback that leaves a separate variable unchanged, use
`LABEL: ${PROMPT_COLOR:-green}`: `LABEL` gets `green`, but no assignment is made
to `PROMPT_COLOR`.

## Required Variables With `:?`

Use `:?` when the stack should fail loudly if a required value is missing:

```yaml
DEPLOY_ROOT: ${DEPLOY_ROOT:?set DEPLOY_ROOT before launching this stack}
```

This is useful for secrets, mount points, or site-specific paths that must be
provided externally.

## Nested Defaults

Defaults can contain other expansions:

```yaml
FOO: ${FOO:=${BAR:=/foo/bar}}
```

If neither `FOO` nor `BAR` is already set, this resolves to:

```bash
FOO=/foo/bar
```

The nested `:=` also makes `BAR` available to subsequent references during
resolution. It does not add an absent `BAR` key to the returned environment or
to the process environment.

Nested expressions are often the cleanest way to define a chain of fallbacks
without repeating the final literal value.

## Mixed Strings

Expansion can appear inside larger strings:

```yaml
PYTHONPATH: ${DEPLOY_ROOT}/lib/python:${PYTHONPATH}
PATH: ${DEPLOY_ROOT}/bin:${PATH}
```

That makes it easy to build derived paths, URLs, prompts, or command lines from
shared variables.

## Explicit Empty Values

An empty string deliberately overrides values from included stacks and the shell:

```yaml
VAR: ""
OTHER: ${VAR}
```

Both resolve to an empty string, even if the shell sets `VAR`. An empty
assignment also resets an accumulated search path. Later stacks can append
new entries without restoring paths from before the reset.

A variable absent from the stack can still fall back to the shell. A
self-reference such as `VAR: ${VAR}` uses the preceding definition, or the
shell when there is no preceding definition.

Default operators apply to the effective value: `${VAR:-default}` returns
`default` when that value is unset or empty, while `${VAR:=default}` also
makes the default available to subsequent references during resolution.
These assignments do not rewrite the original stack definitions. A default
assigned by a self-reference stays local to that definition; other variables
still see its complete final value, including any appended suffixes.

## Self-References Across Includes

When a stack extends its own variable, `${VAR}` uses the value built by earlier
sources in load order. The process environment supplies the initial value when
no earlier source defines it. Shared includes are loaded only once.

For example, with `PYTHONPATH=ORIG` in the shell:

```yaml
# default.env
all:
  PYTHONPATH: /base:${PYTHONPATH}

# toola.env
include: [default]
all:
  PYTHONPATH: ${PYTHONPATH}:/toola

# toolb.env
include: [default]
all:
  PYTHONPATH: ${PYTHONPATH}:/toolb

# app.env
include: [toola, toolb]
all:
  PYTHONPATH: ${PYTHONPATH}:/app
```

Loading `app` produces `/base:ORIG:/toola:/toolb:/app`. Loading `toola toolb`
produces `/base:ORIG:/toola:/toolb`. With the shell variable unset or empty,
the `ORIG` component is omitted. A literal assignment such as
`PYTHONPATH: /replacement` resets the accumulated value.

These rules apply to `PATH` and custom variables as well as `PYTHONPATH`. See
[Tools and inheritance](examples/tools.md) for versioned package
paths and Windows native-library directories.

References to other variables still use the final stack definitions, allowing
an application to override a tool root used by an inherited path. Platform
sections and path delimiters follow the platform selected when loading the
environment, even when it differs from the host platform.

Aliases also remain late-bound. For example, if a base stack defines
`FOO: /base` and `BAR: ${FOO}`, and an application stack includes it and overrides
`FOO: ${BAR}:/app`, both variables resolve to `/base:/app`. The indirect
self-reference uses the earlier definition of `FOO` to break the cycle.
Unlike sequential shell assignments, `BAR` does not capture a snapshot of
`FOO` when it is defined. YAML key order does not determine resolution order.

## Template Tokens Stay Literal

envstack only resolves `${NAME}`-style expressions.

Brace tokens such as `{show}` or `{shot}` are preserved as literal template
placeholders:

```yaml
NUKESCRIPT: ${ROOT}/projects/{show}/{shot}/comp/{show}_{shot}.{version}.nk
```

If `ROOT` resolves to `/mnt/pipe`, the remaining `{show}`-style placeholders
stay intact for downstream tooling.

## Command Substitution

Variable expansion and command substitution can be combined:

```yaml
PYVERSION: $(python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")
PYTHONPATH: ${DEPLOY_ROOT}/lib/python${PYVERSION}
```

Set `ALLOW_COMMANDS=1` before launching envstack or importing it in Python.
Command substitution recognizes a whole value of the form `$(...)`; it is not
shell-style interpolation into arbitrary surrounding text. Successful output is
stripped of leading and trailing whitespace. Command execution starts with the launching process environment and overlays
the resolved default stack. Put the intended interpreter on `PATH` before
starting envstack, and ensure the default stack preserves that selection.

Loading can resolve values internally to update `ENVPATH`, and dependency lookup
can evaluate a value more than once. Do not rely on a command running exactly
once or only when you request that variable with `-r`.

## YAML Transformation Tags

Built-in tags apply to scalar values. A tag in a file describes the stored
representation; it is not a parameter modifier.

| Tag | Loading and resolution | Writing YAML |
| --- | --- | --- |
| `!base64` | Decode the stored Base64 payload before expanding its contents | Encode a newly constructed `Base64Node`; preserve an unchanged payload loaded from YAML |
| `!aesgcm` | Decrypt with `ENVSTACK_SYMMETRIC_KEY`, then expand | Encrypt a new `AESGCMNode`; preserve an unchanged loaded payload |
| `!fernet` | Decrypt with `ENVSTACK_FERNET_KEY`, then expand | Encrypt a new `FernetNode`; preserve an unchanged loaded payload |
| `!encrypt` | Select AES-GCM, then Fernet, then Base64 according to available keys | Use the same selection for a new `EncryptedNode`; preserve an unchanged loaded payload |
| `!md5` | Return the stored text; resolution does not compute a hash | Hash the node's current text when serializing |

Base64 is encoding, not encryption. MD5 is a digest, not encryption and not a
password-storage mechanism. See [Secrets and encryption](secrets.md) for keys
and encrypted-file workflows. For `!encrypt`, use a key context compatible with
the one used when writing the payload; the tag does not identify its algorithm.

For example, writing `MD5Node("hello")` produces
`!md5 '5d41402abc4b2a76b9719d911017c592'`. Loading `!md5 hello` alone does not
hash `hello`. Serializing that loaded MD5 node hashes its current text again;
unlike the encryption nodes, it does not preserve an unchanged loaded payload.

### Compose Context, Tags, and Modifiers

Save this as `context.env`:

```yaml
all:
  ROOT: ${ROOT:-/shared}
  ENV: ${ENV:-prod}
  DEPLOY_ROOT: !base64 JHtST09UfS8ke0VOVn0=
  LIB: ${DEPLOY_ROOT}/lib/python
```

The Base64 payload represents the literal expression `${ROOT}/${ENV}`. With
`ROOT=/studio` and `ENV=dev` in the launching shell:

```bash
envstack context -r DEPLOY_ROOT LIB
```

produces:

```text
DEPLOY_ROOT=/studio/dev
LIB=/studio/dev/lib/python
```

Without those shell values, the defaults produce `/shared/prod` and
`/shared/prod/lib/python`. The tag decodes the expression, the modifiers select
context values, and ordinary references compose the final paths. Use
`envstack context -u DEPLOY_ROOT` to inspect the stored payload instead.

## Evaluation Order

1. Read YAML, construct tagged nodes, and process YAML anchors and merge keys.
   Load included sources in order and select the requested platform section.
   If that section is absent, use `all`; use `<<: *all` in a platform section
   when it should inherit an anchored `all` mapping.
2. Assemble the final stack and retain earlier definitions for self-references.
   `load_environ()` returns unresolved values, but internally resolves the
   environment to update `ENVPATH` between requested stacks.
3. Decode or decrypt top-level tagged values using the available key context.
   Process-environment encryption keys take precedence over same-named stack
   keys during resolution.
4. Resolve dependencies and modifiers on demand. Ordinary references use final
   definitions; self-references fall back through preceding definitions. An
   eligible `$(...)` value runs when evaluated if commands are enabled.
5. Normalize and deduplicate path-like results using the selected platform,
   then restore supported Python literal types in top-level results.
6. Apply the result only when requested. `resolve_environ()` returns a new
   environment; `init()` updates `os.environ` and `sys.path`, while a wrapped
   command receives its own composed environment.

This is dependency resolution, not sequential execution of YAML assignments.
Avoid using key order as a way to control effects. `:=` can retain assignments
for subsequent references, so use explicit variable definitions when several
independent expressions need the same default.

Lists and dictionaries are traversed for variable expansion. Keep encoded or
encrypted expressions at the top level when composing tags with modifiers:
nested tagged values do not follow the same top-level decode-then-expand path.

A cycle uses earlier definitions when possible. Without an earlier or shell
value, a plain recursive reference contributes an empty string; default and
required-value operators can instead supply a fallback or raise an error.
YAML `null` is distinct from `""`; it is not an instruction to unset a variable.

## See Also

- [Default example](examples/default.md): practical stack examples using nested
  defaults and derived paths
- [Python API](api.md): loading and resolving environments programmatically
- [FAQ](faq.md): operational tradeoffs and common envstack questions
