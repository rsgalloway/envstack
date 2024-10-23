import pytest
from envstack.env import Env, EnvVar, Source, Scope
from envstack.env import clear_file_cache, load_file_cache, safe_eval
from envstack.env import build_sources, expandvars, load_environ, load_file
from envstack.env import trace_var, getenv

def test_EnvVar_substitute():
    v = EnvVar('$FOO:${BAR}')
    assert v.substitute(FOO='foo', BAR='bar') == 'foo:bar'

def test_EnvVar_eq():
    v1 = EnvVar('$FOO')
    v2 = EnvVar('$FOO')
    assert v1 == v2

def test_EnvVar_iter():
    v = EnvVar('$FOO:${BAR}')
    assert list(v) == ['FOO', 'BAR']

def test_EnvVar_getitem():
    v = EnvVar('$FOO:${BAR}')
    assert v['FOO'] == '$FOO'
    assert v['BAR'] == '${BAR}'

def test_EnvVar_setitem():
    v = EnvVar('$FOO:${BAR}')
    v['FOO'] = 'foo'
    v['BAR'] = 'bar'
    assert v.substitute() == 'foo:bar'

def test_EnvVar_append():
    v = EnvVar('$FOO')
    v.append(':${BAR}')
    assert v.substitute(FOO='foo', BAR='bar') == 'foo:bar'

def test_EnvVar_extend():
    v = EnvVar('$FOO')
    v.extend([':${BAR}', ':${BAZ}'])
    assert v.substitute(FOO='foo', BAR='bar', BAZ='baz') == 'foo:bar:baz'

def test_EnvVar_expand():
    v = EnvVar('$FOO:${BAR}')
    assert v.expand(env={'FOO': 'foo', 'BAR': 'bar'}) == 'foo:bar'

def test_EnvVar_get():
    v = EnvVar('$FOO:${BAR}')
    assert v.get('FOO') == '$FOO'
    assert v.get('BAR') == '${BAR}'
    assert v.get('BAZ') == None
    assert v.get('BAZ', default='baz') == 'baz'

def test_EnvVar_items():
    v = EnvVar('$FOO:${BAR}')
    assert list(v.items()) == [('FOO', '$FOO'), ('BAR', '${BAR}')]

def test_EnvVar_keys():
    v = EnvVar('$FOO:${BAR}')
    assert list(v.keys()) == ['FOO', 'BAR']

def test_EnvVar_parts():
    v = EnvVar('$FOO:${BAR}')
    assert list(v.parts()) == ['$FOO', '${BAR}']

def test_EnvVar_value():
    v = EnvVar('$FOO:${BAR}')
    assert v.value() == '$FOO:${BAR}'

def test_EnvVar_vars():
    v = EnvVar('$FOO:${BAR}')
    assert v.vars() == {'FOO', 'BAR'}

def test_Env_getitem():
    env = Env({'BAR': '$FOO', 'BAZ': '$BAR'})
    assert env['BAR'] == None

def test_Env_update():
    env = Env({'BAR': '$FOO', 'BAZ': '$BAR'})
    env.update({'FOO': 'foo'})
    assert env['BAZ'] == 'foo'

def test_Env_get():
    env = Env({'BAR': '$FOO', 'BAZ': '$BAR'})
    assert env.get('BAZ') == None
    assert env.get('BAZ', resolved=False) == '$BAR'

def test_Env_get_raw():
    env = Env({'BAR': '$FOO', 'BAZ': '$BAR'})
    assert env.get_raw('BAZ') == '$BAR'

def test_Env_items():
    env = Env({'BAR': '$FOO', 'BAZ': '$BAR'})
    assert list(env.items()) == [('BAR', None), ('BAZ', None)]

def test_Env_merge():
    env1 = Env({'BAR': '$FOO'})
    env2 = Env({'FOO': 'foo'})
    env1.merge(env2)
    assert env1['BAR'] == 'foo'

def test_Env_copy():
    env = Env({'BAR': '$FOO'})
    env_copy = env.copy()
    assert env_copy['BAR'] == '$FOO'

def test_Scope_init():
    scope = Scope('/path/to/scope')
    assert scope.path == '/path/to/scope'

def test_Source_eq():
    source1 = Source('/path/to/source')
    source2 = Source('/path/to/source')
    assert source1 == source2

def test_Source_ne():
    source1 = Source('/path/to/source1')
    source2 = Source('/path/to/source2')
    assert source1 != source2

def test_Source_hash():
    source = Source('/path/to/source')
    assert hash(source) == hash('/path/to/source')

def test_Source_repr():
    source = Source('/path/to/source')
    assert repr(source) == "Source('/path/to/source')"

def test_Source_str():
    source = Source('/path/to/source')
    assert str(source) == '/path/to/source'

def test_Source_exists():
    source = Source('/path/to/source')
    assert source.exists() == True

def test_Source_includes():
    source = Source('/path/to/source')
    assert source.includes() == []

def test_Source_length():
    source = Source('/path/to/source')
    assert source.length() == 0

def test_Source_load():
    source = Source('/path/to/source')
    assert source.load() == None

def test_clear_file_cache():
    clear_file_cache()
    assert load_file_cache == {}

def test_safe_eval():
    assert safe_eval('1 + 1') == 2

def test_build_sources():
    sources = build_sources()
    assert sources == []

def test_expandvars():
    assert expandvars('$FOO', env={'FOO': 'foo'}) == 'foo'
    assert expandvars('$FOO:${BAR}', env={'FOO': 'foo', 'BAR': 'bar'}) == 'foo:bar'

def test_load_environ():
    environ = load_environ()
    assert isinstance(environ, Env)

def test_load_file():
    assert load_file('/path/to/file') == None

def test_trace_var():
    trace_var('name', 'var', scope='/path/to/scope')

def test_getenv():
    assert getenv('key') == None
    assert getenv('key', default='default') == 'default'