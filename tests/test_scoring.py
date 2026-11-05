"""Unit tests for verdicts and gap-score aggregation."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.model import Evidence
from cdc.scoring import verdict


def E(channel, *provenance):
    return Evidence(claim="c1", element="m:f", channel=channel,
                    provenance=frozenset(provenance), strength=1.0)


def test_broad_support_is_supported():
    ev = [E("NAME", "ch:NAME", "tok:aes", "file:a.py"),
          E("DOC", "ch:DOC", "tok:gcm", "file:b.py"),
          E("IMPORT", "ch:IMPORT", "lib:cryptography", "file:c.py")]
    assert verdict(ev, k_min=2) == "SUPPORTED"


def test_support_that_does_not_survive_ablation_is_weak():
    ev = [E("NAME", "ch:NAME", "tok:aes", "file:a.py"),
          E("DOC", "ch:DOC", "tok:gcm", "file:b.py")]
    assert verdict(ev, k_min=2) == "WEAK"


def test_name_only_support_is_unsupported():
    ev = [E("NAME", "ch:NAME", "tok:aes", "file:a.py"),
          E("DOC", "ch:DOC", "tok:aes", "file:a.py")]
    assert verdict(ev, k_min=2) == "UNSUPPORTED"


def test_no_evidence_is_unsupported():
    assert verdict([], k_min=2) == "UNSUPPORTED"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")
