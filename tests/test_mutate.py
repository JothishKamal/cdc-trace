"""Unit tests for the labelled mutation operators."""
import ast
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.model import Claim, CodeElement
from cdc.mutate import OPERATORS, apply_mutations, mutate_source

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


def test_delete_only_method_keeps_class_parseable():
    src = "class Foo:\n    def bar(self):\n        return 1\n"
    out = mutate_source(src, "bar", "DELETE")
    tree = ast.parse(out)
    foo = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    assert foo.name == "Foo"
    assert "bar" not in names(out)


def test_apply_mutations_targets_single_homonym():
    src_text = (
        "class A:\n"
        "    def run(self):\n"
        "        return 'a'\n"
        "\n"
        "class B:\n"
        "    def run(self):\n"
        "        return 'b'\n"
    )
    parsed = ast.parse(src_text)
    a_run = parsed.body[0].body[0]
    el = CodeElement(
        uid="m:A.run", kind="method", name="run", path="m.py",
        lineno=a_run.lineno, doc="", imports=frozenset(),
        calls=frozenset(), body_ops=frozenset(), is_stub=False, reachable=True,
    )
    claim = Claim(
        cid="c1", component="c", text="t", kind="algorithm",
        terms=frozenset({"run"}), implied_libs=frozenset(), section="s",
    )

    class _DeleteRng:
        def shuffle(self, x):
            pass

        def choice(self, seq):
            return "DELETE"

    with tempfile.TemporaryDirectory() as tmp:
        src_root = os.path.join(tmp, "src")
        dst_root = os.path.join(tmp, "dst")
        os.makedirs(src_root)
        with open(os.path.join(src_root, "m.py"), "w", encoding="utf-8") as fh:
            fh.write(src_text)
        muts = apply_mutations(
            src_root, dst_root, [claim], [el], _DeleteRng(), rate=1.0,
        )
        assert len(muts) == 1 and muts[0].target_uid == "m:A.run"
        with open(os.path.join(dst_root, "m.py"), encoding="utf-8") as fh:
            out = fh.read()
    tree = ast.parse(out)
    class_a = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "A")
    class_b = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "B")
    assert not any(isinstance(n, ast.FunctionDef) and n.name == "run" for n in class_a.body)
    b_runs = [n for n in class_b.body if isinstance(n, ast.FunctionDef)]
    assert len(b_runs) == 1 and b_runs[0].name == "run"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")
