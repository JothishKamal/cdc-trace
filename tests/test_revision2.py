"""Invariants of the second-round experiments (experiments/revision2.py)."""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.codebase import _is_stub
from cdc.model import Evidence
from experiments.revision2 import (
    STUB_FORMS_NEW, STUB_FORMS_ORIG, _bad_except, _drop_branch, _is_stub_ext,
    _wrong_param, make_stub, stub_applicable, weighted_C,
)

SRC = '''
def fetch(url, retries):
    """Fetches url."""
    try:
        if retries > 3:
            log("many")
        return get(url, timeout=30)
    except OSError:
        raise
'''


def _func():
    return ast.parse(SRC).body[0]


def test_new_faults_change_code_and_stay_valid():
    for fn in (_wrong_param, _drop_branch, _bad_except):
        f = _func()
        assert fn(f), fn.__name__
        out = ast.unparse(f)
        ast.parse(out)
        assert out != ast.unparse(_func()), fn.__name__


def test_drop_branch_keeps_raise_guards():
    f = ast.parse("def g(x):\n    if x < 0:\n        raise ValueError\n    return x\n").body[0]
    assert not _drop_branch(f)


def test_wider_detector_is_a_superset_of_the_original():
    for form in STUB_FORMS_ORIG:
        f = _func()
        make_stub(f, form)
        assert _is_stub(f), form
        assert _is_stub_ext(f, set()), form


def test_wider_detector_flags_every_new_form():
    for form in STUB_FORMS_NEW:
        f = _func()
        assert stub_applicable(f, form), form
        make_stub(f, form)
        assert not _is_stub(f), form
        assert _is_stub_ext(f, {"_pending"}), form


def test_wider_detector_leaves_real_code_alone():
    assert not _is_stub_ext(_func(), set())


def _ev(prov, s):
    return Evidence("c", "e", "NAME", frozenset(prov), s)


def test_weighted_count_respects_disjointness():
    items = [_ev({"a", "x"}, 0.3), _ev({"a"}, 0.8), _ev({"b"}, 0.8)]
    assert abs(weighted_C(items) - 1.6) < 1e-9
    assert weighted_C([]) == 0.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")
