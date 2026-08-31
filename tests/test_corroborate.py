"""Unit tests for the corroboration engine."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.corroborate import (ablate, corroboration, counterfactual_worst,
                             dependency_components, sources, witness_set)
from cdc.model import Evidence


def E(channel, *provenance, claim="c1", element="m:f"):
    return Evidence(claim=claim, element=element, channel=channel,
                    provenance=frozenset(provenance), strength=1.0)


def test_three_name_derived_evidences_are_one_witness():
    """The worked case: three matches, all moved by the same identifier."""
    ev = [E("NAME", "ch:NAME", "tok:aes", "file:a.py"),
          E("NAME", "ch:NAME", "tok:aes", "file:b.py"),
          E("NAME", "ch:NAME", "tok:aes", "file:c.py")]
    assert len(ev) == 3
    assert corroboration(ev) == 1


def test_provenance_sharing_is_not_transitive():
    """e1-e2 share a token, e2-e3 share a file, yet e1 and e3 are disjoint."""
    ev = [E("NAME", "ch:NAME", "tok:aes", "file:a.py"),
          E("DOC", "ch:DOC", "tok:aes", "file:b.py"),
          E("IMPORT", "ch:IMPORT", "lib:cryptography", "file:b.py")]
    assert len(dependency_components(ev)) == 1       # one connected group
    assert corroboration(ev) == 2                    # but e1 and e3 are disjoint


def test_witness_set_is_exactly_maximum_and_pairwise_disjoint():
    ev = [E("NAME", "ch:NAME", "tok:aes", "file:a.py"),
          E("DOC", "ch:DOC", "tok:gcm", "file:b.py"),
          E("IMPORT", "ch:IMPORT", "lib:cryptography", "file:c.py"),
          E("BODY", "ch:BODY", "op:xor", "file:a.py")]
    idx = witness_set(ev)
    assert len(idx) == corroboration(ev) == 3
    seen = set()
    for i in idx:
        assert not (ev[i].provenance & seen)
        seen |= set(ev[i].provenance)


def test_ablation_removes_every_evidence_touching_a_source():
    ev = [E("NAME", "ch:NAME", "tok:aes", "file:a.py"),
          E("DOC", "ch:DOC", "tok:gcm", "file:b.py")]
    assert len(ablate(ev, "ch:NAME")) == 1
    assert len(ablate(ev, "tok:aes")) == 1
    assert len(ablate(ev, "file:zzz.py")) == 2


def test_counterfactual_demotes_a_name_dependent_claim():
    """C = 2, but the whole margin rests on the naming channel."""
    ev = [E("NAME", "ch:NAME", "tok:aes", "file:a.py"),
          E("DOC", "ch:DOC", "tok:gcm", "file:b.py")]
    assert corroboration(ev) == 2
    worst, source = counterfactual_worst(ev)
    assert worst == 1
    assert source in {"ch:NAME", "tok:aes", "file:a.py",
                      "ch:DOC", "tok:gcm", "file:b.py"}


def test_counterfactual_survives_when_support_is_genuinely_broad():
    ev = [E("NAME", "ch:NAME", "tok:aes", "file:a.py"),
          E("DOC", "ch:DOC", "tok:gcm", "file:b.py"),
          E("IMPORT", "ch:IMPORT", "lib:cryptography", "file:c.py")]
    assert corroboration(ev) == 3
    worst, _ = counterfactual_worst(ev)
    assert worst == 2


def test_sources_are_sorted_and_deduplicated():
    ev = [E("NAME", "ch:NAME", "tok:aes"), E("DOC", "ch:DOC", "tok:aes")]
    assert sources(ev) == ["ch:DOC", "ch:NAME", "tok:aes"]


def test_empty_evidence_is_zero_corroboration():
    assert corroboration([]) == 0
    assert witness_set([]) == []
    assert counterfactual_worst([]) == (0, "")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")
