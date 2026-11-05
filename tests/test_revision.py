"""Invariants of the review-response experiments (experiments/revision.py)."""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.evidence import gather
from cdc.model import Claim, CodeElement
from experiments.revision import DEFAULT, _SEM, cfg_of, claim_ops_ok, gather_v

SRC = '''
def check(x):
    """Validates x."""
    if x < 0:
        raise ValueError("negative")
    if x > 10:
        return x - 10
    return x
'''


def _el(name, ops=frozenset(), stub=False, calls=frozenset(), kind="function", path="m.py"):
    return CodeElement(uid=f"m:{name}", kind=kind, name=name, path=path, lineno=1, doc="",
                       imports=frozenset(), calls=calls, body_ops=ops, is_stub=stub,
                       reachable=True)


def _claim(terms):
    return Claim(cid="c1", component="x", text=" ".join(terms), kind="requirement",
                 terms=frozenset(terms), implied_libs=frozenset(), section="1")


BASE_OPS = ("NEGATE_COND", "DROP_GUARD", "CONST_RETURN")


def test_semantic_operators_change_code_and_stay_valid():
    # experiments/revision2.py adds operators to _SEM on import; those need other
    # source shapes and are tested in test_revision2.py.
    for op in BASE_OPS:
        fn = _SEM[op]
        tree = ast.parse(SRC)
        assert fn(tree.body[0]), op
        out = ast.unparse(tree)
        ast.parse(out)
        assert out != ast.unparse(ast.parse(SRC)), op


def test_drop_guard_removes_only_raising_ifs():
    tree = ast.parse(SRC)
    _SEM["DROP_GUARD"](tree.body[0])
    out = ast.unparse(tree)
    assert "raise" not in out and "x - 10" in out


def test_default_configuration_reproduces_gather():
    claim = _claim(["hash", "entry"])
    els = [_el("hash_entry", ops=frozenset({"op:hash"})),
           _el("main", calls=frozenset({"hash_entry"}), path="app.py")]
    assert sorted(map(repr, gather(claim, els))) == sorted(map(repr, gather_v(claim, els, DEFAULT)))


def test_stub_gate_switch_only_affects_stubs():
    claim = _claim(["hash", "entry"])
    els = [_el("hash_entry", stub=True),
           _el("main", calls=frozenset({"hash_entry"}), path="app.py")]
    gated = {e.channel for e in gather_v(claim, els, DEFAULT)}
    ungated = {e.channel for e in gather_v(claim, els, cfg_of("no_stub_gate"))}
    assert "CALL" not in gated and "CALL" in ungated


def test_channel_only_tags_drop_files_and_tokens():
    claim = _claim(["hash", "entry"])
    els = [_el("hash_entry", ops=frozenset({"op:hash"}))]
    for e in gather_v(claim, els, cfg_of("tags_channel_only")):
        assert e.provenance == frozenset({f"ch:{e.channel}"})


def test_claim_ops_rejects_weak_counterpart():
    claim = _claim(["sha256", "hash"])
    assert claim_ops_ok(claim, _el("f", ops=frozenset({"op:hash"})))
    assert not claim_ops_ok(claim, _el("f", ops=frozenset({"op:hash_weak"})))


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")
