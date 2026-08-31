"""Unit tests for the labelled mutation operators."""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.mutate import OPERATORS, mutate_source

SRC = '''
import hashlib


def digest_token(value):
    """Hashes the token with SHA-256."""
    return hashlib.sha256(value).hexdigest()
'''


def names(source):
    return {n.name for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.FunctionDef)}


def test_delete_removes_the_function():
    out = mutate_source(SRC, "digest_token", "DELETE")
    assert "digest_token" not in names(out)


def test_rename_keeps_behaviour_and_drops_the_name():
    out = mutate_source(SRC, "digest_token", "RENAME")
    assert "digest_token" not in names(out)
    assert "sha256" in out               # behaviour intact


def test_weaken_substitutes_a_weaker_algorithm():
    out = mutate_source(SRC, "digest_token", "WEAKEN")
    assert "digest_token" in names(out)  # name intact
    assert "sha256" not in out
    assert "md5" in out


def test_stub_removes_the_body_and_the_docstring():
    out = mutate_source(SRC, "digest_token", "STUB")
    assert "digest_token" in names(out)
    assert "NotImplementedError" in out
    assert "SHA-256" not in out


def test_nominal_keeps_name_and_docstring_but_guts_the_body():
    """The adversary: indistinguishable from working code by name alone."""
    out = mutate_source(SRC, "digest_token", "NOMINAL")
    assert "digest_token" in names(out)
    assert "SHA-256" in out              # docstring intact
    assert "sha256" not in out.replace("SHA-256", "")   # implementation gone
    assert "NotImplementedError" not in out             # and it does not announce itself


def test_every_operator_produces_parseable_python():
    for op in OPERATORS:
        ast.parse(mutate_source(SRC, "digest_token", op))


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")
