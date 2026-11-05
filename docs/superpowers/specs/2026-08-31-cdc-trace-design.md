# Channel-Disjoint Corroboration for Traceability-Gap Detection

**Design specification — BCSE497J Project-I, Review 2**
Date: 2026-08-31
Project title (fixed at Review 1, not modifiable): *Traceability-Gap Detection Between Student Code and Thesis Claims*

---

## 1. Problem

A claims document — a thesis, a design document, an architecture README — asserts that a
system does certain things. The source code either does them or it does not. Deciding
which, by hand, is slow and subjective, and it does not scale.

Automated traceability-link recovery already exists and is mature. The failure it does
not address is this: **a claim is not implemented merely because some code resembles it.**

Consider a document claiming *"AES-GCM encrypts the session token"* against code
containing:

```python
def aes_gcm_encrypt_token(token):
    """Encrypts the session token with AES-GCM."""
    raise NotImplementedError
```

Lexical matching says implemented. Embedding similarity says implemented. An LLM shown
that signature says implemented. All three agree — and all three agree **for one reason**,
which is the identifier string. Rename the function to `f7` and every one of them
collapses at the same instant. Their agreement was never three independent judgements; it
was one signal counted three times.

This is the traceability analogue of counting correlated votes as independent witnesses.
Weighting the matchers does not fix it, because a weighting rescales all of them together
and cannot change the ordering when the correlated signal is the dominant one.

## 2. Core idea

Gather evidence for each claim through **provenance-tagged channels**, then count only the
evidence that is *mutually independent*.

| Channel | Evidence that the claim is real |
|---|---|
| `NAME` | an identifier or path lexically encodes the claim |
| `DOC` | a docstring or comment asserts it |
| `IMPORT` | the library the claim implies is actually imported |
| `CALL` | the element is reachable from an entry point in the call graph |
| `SCHEMA` | a table, route or config key the claim names exists |
| `TEST` | a test exercises the element |
| `BODY` | the body performs the operations the claim implies, and is not a stub |

Each piece of evidence carries a **set** of provenance sources, not a single tag. Two
pieces of evidence are *dependent* when their provenance sets intersect.

```
claim: "AES-GCM encrypts the session token"

  e1  NAME    aes_gcm_encrypt_token        {ch:NAME,   tok:aes_gcm, file:crypto/aes.py}
  e2  DOC     "...encrypts with AES-GCM"   {ch:DOC,    tok:aes_gcm, file:crypto/aes.py}
  e3  IMPORT  from cryptography import ... {ch:IMPORT, lib:cryptography, file:session.py}

  naive count  : 3 matches  ->  IMPLEMENTED
  corroboration: e1 and e2 are dependent (shared token, shared file)
                 ->  C = 2, not 3
```

`e2` looks like fresh corroboration and is not: the docstring merely restates the identifier.

**Definition.** `C(claim)` is the size of the largest set of evidence for that claim whose
provenance sets are **pairwise disjoint**. It is a maximum independent set over the
conflict graph whose edges are shared provenance. It counts genuinely separate reasons to
believe the claim, not agreeing signals.

**Counterfactual requirement.** For every provenance source present, delete all evidence
touching it and recompute `C`. A verdict must survive the loss of any single source. A
claim propped up entirely by naming does not survive.

Set-valued provenance is load-bearing. If each piece of evidence carried a single channel
tag, "channel-disjoint" would collapse into counting distinct channels and the maximum
independent set would be decoration. It is also why connected components are the wrong
tool: `e1` may share a token with `e2` and `e2` share a file with `e3` while `e1` and `e3`
remain disjoint, so the transitive closure over-merges.

## 3. Scope

**In scope for Review 2**

- Python AST extraction: functions, classes, methods, routes, schema elements, imports,
  call graph, test references.
- Claim extraction from Markdown and LaTeX documents behind one interface.
- All seven evidence channels.
- The corroboration engine: dependency classification, `C(claim)`, counterfactual ablation.
- Labelled mutation corpus with five operators.
- Eight comparison policies, including the Review 1 proposal as a baseline.
- Experiments E0–E6, figures, dependency-free tests, README.
- Draft report sections, slide content, demo script.

**Deferred to the Final Review, stated openly in the deck**

- Live LLM claim-extraction backend.
- Corpus scale-up beyond the vendored set.
- Cross-language extraction beyond Python.
- Oral-probe question generation for high-gap components.

**Explicit non-goals.** Plagiarism or authorship detection; grading; judging code quality;
proving code correct. The system localises which claims lack independent implementation
evidence, and nothing more.

## 4. Architecture

```
        claims document                       code archive
       (Markdown / LaTeX)                     (Python repo)
              |                                     |
      [300] claim extraction              [200] code extraction
      rule-based default                   AST inventory, call graph,
      (LLM backend deferred)               routes, schema, imports, tests
              |                                     |
              +------------------+------------------+
                                 |
                    [400] evidence generation
                    seven channels, provenance-tagged
                                 |
                    [500] corroboration engine
                    510 dependency classification
                    520 C(claim) = max disjoint set
                    530 counterfactual ablation
                                 |
                    [600] scoring and policies
                    per-claim verdict -> per-component
                    -> per-document gap score
                                 |
                    [800] experiments and figures
                         ^
                         |
                    [700] mutation corpus (labels by construction)
```

### Module map

| ID | File | Role |
|---|---|---|
| 100 | `cdc/model.py` | `Claim`, `CodeElement`, `Evidence`, `Verdict`, `GapReport` |
| 200 | `cdc/codebase.py` | AST inventory, call graph, reachability, routes, schema |
| 300 | `cdc/claims.py` | claim extraction; Markdown and LaTeX frontends |
| 400 | `cdc/evidence.py` | the seven channels, provenance construction |
| 500 | `cdc/corroborate.py` | dependency graph, exact `C(claim)`, ablation |
| 600 | `cdc/scoring.py`, `cdc/policies.py` | verdicts, gap scores, all policies |
| 700 | `cdc/mutate.py` | labelled fault injection |
| 800 | `experiments/`, `figures/` | E0–E6, results.json, plots |

### Repository layout

```
cdc-trace/
├── README.md              headline results and honest limitations
├── requirements.txt       numpy, matplotlib
├── LICENSE                MIT
├── cdc/                   the package (modules 100-700)
├── corpus/                vendored repos, documents, manifest.json
├── experiments/           run_all.py, report.py
├── figures/               make_figures.py
├── results/               results.json
├── assets/                fig1..fig6.png
├── tests/                 dependency-free unit tests
└── docs/                  draft report, slide content, demo script
```

## 5. Data model (module 100)

```python
@dataclass(frozen=True)
class CodeElement:
    uid: str                    # "pkg.mod:Class.method"
    kind: str                   # function|class|method|route|table|config|test
    name: str
    path: str
    lineno: int
    doc: str
    imports: FrozenSet[str]
    calls: FrozenSet[str]
    body_ops: FrozenSet[str]    # normalised operation vocabulary from the AST
    is_stub: bool
    reachable: bool             # from a declared entry point

@dataclass(frozen=True)
class Claim:
    cid: str
    component: str              # component or section the claim belongs to
    text: str
    kind: str                   # architecture|algorithm|requirement|interface|data
    terms: FrozenSet[str]       # normalised content terms
    implied_libs: FrozenSet[str]
    section: str

@dataclass(frozen=True)
class Evidence:
    claim: str
    element: str
    channel: str                # NAME|DOC|IMPORT|CALL|SCHEMA|TEST|BODY
    provenance: FrozenSet[str]  # {"ch:NAME", "tok:aes_gcm", "file:crypto/aes.py"}
    strength: float             # [0,1]
```

Provenance source tags are namespaced: `ch:` channel, `tok:` shared normalised sub-token,
`file:` source file, `lib:` imported library, `sym:` imported symbol. Disjointness is plain
set intersection over these strings.

A channel emits one `tok:` source **per normalised sub-token shared between the claim terms
and the element identifier**, so the `aes_gcm_encrypt_token` match against the claim above
contributes `tok:aes` and `tok:gcm`. Sub-tokens are produced by splitting camelCase and
snake_case, lowercasing, and dropping a small stop-list of structural words (`get`, `set`,
`handler`, `util`, and similar) that carry no claim content.

`strength` governs **emission only**: a channel does not emit evidence below its minimum
strength, and the value is carried through to the report so a reader can see how strong
each surviving piece of evidence was. It plays no part in disjointness and no part in
`C(claim)`, both of which are purely set-theoretic. This is deliberate — making the count
strength-weighted would reintroduce exactly the rescaling that the method argues cannot fix
correlated agreement.

## 6. Corroboration engine (module 500)

- **510 dependency classification.** Build the conflict graph over the evidence for one
  claim: an edge whenever provenance sets intersect. Connected components are reported in
  the evidence bundle for explanation, but the verdict uses the stricter pairwise-disjoint
  measure, because transitive closure over-merges.
- **520 corroboration quantity.** `C(claim)` and one witnessing evidence set, by exact
  branch-and-bound maximum independent set with a highest-degree pivot and a
  size-plus-remaining bound prune. Evidence per claim is capped at 24 for bounded work;
  the cap is recorded in the output whenever it binds.
- **530 counterfactual ablation.** For each provenance source present, remove all evidence
  touching it and recompute `C`. Report the worst-case `C` and the source responsible.

**Verdict.** With `k_min = 2` by default:

| Verdict | Condition |
|---|---|
| `SUPPORTED` | `C >= k_min` and worst-case ablated `C >= k_min` |
| `WEAK` | `C >= k_min` but ablation drops it below |
| `UNSUPPORTED` | `C < k_min` |

For the binary evaluation in §9, a policy must answer *implemented or not*. The two claimed
policies differ precisely in how they treat `WEAK`: `cdc` accepts it as implemented, and
`cdc_counterfactual` rejects it. That single disagreement is what E4 measures, and it is
the whole value of the counterfactual requirement.

The identifier-ablation experiment is the same operation applied wholesale: remove every
`ch:NAME` and every `tok:` source at once, and re-run.

## 7. Ground truth (module 700)

Ground truth is **mutation-injected and labelled by construction**, so precision and recall
are exact and the whole run reproduces from a seed. The corpus is a small vendored set of
permissively-licensed Python repositories that ship substantial design documentation; that
document is treated as the claims artifact. Vendoring means the demonstration needs no
network access.

| Operator | Transformation | Defeats |
|---|---|---|
| `DELETE` | remove the claimed element entirely | nothing — the easy case |
| `RENAME` | opaque identifier, behaviour intact | lexical, embedding |
| `WEAKEN` | substitute a weaker algorithm | lexical, embedding, channel-count |
| `STUB` | body becomes `pass` / `NotImplementedError` | all but `BODY` and `CALL` |
| `NOMINAL` | **keep name and docstring, gut the body** | **every baseline** |

`NOMINAL` is the adversary the method exists to catch. Each mutation records the claim it
targets, the operator, and the element touched — that record is the label.

Mutations are applied to a copy of the corpus tree. The pristine corpus is never modified.

## 8. Policies compared (module 600)

One dict, one signature, thresholds swept independently.

| Policy | Rule |
|---|---|
| `lexical` | identifier Jaccard above a threshold |
| `embedding` | cosine similarity above a threshold |
| `hybrid` | **the Review 1 proposal**: structural overlap combined with semantic similarity |
| `evidence_count` | count evidence, ignore dependence |
| `channel_count` | count distinct channels, ignore shared tokens and files |
| `cdc` | `C(claim) >= k_min` |
| `cdc_counterfactual` | `cdc` plus ablation survival — **the claimed policy** |
| `llm_judge` | optional, from cached verdicts |

Every baseline with a free threshold has it **swept and set to its own best operating
point**, with the full sweep reported, so the comparison cannot be an artefact of a
threshold chosen to flatter the claimed policy.

**Embedding backend.** The default is TF-IDF over identifier sub-tokens (camelCase and
snake_case split), cosine similarity, numpy only. The README states plainly that this is a
lexical-semantic proxy rather than a neural embedding, with a MiniLM backend available
behind the same interface for anyone who wants one.

## 9. Experiments (module 800)

Deterministic, one seed, written to `results/results.json`; `report.py` prints the tables.

| ID | Experiment | Output |
|---|---|---|
| E0 | threshold sweep for every free-threshold baseline | operating points, reported in full |
| E1 | main comparison | precision, recall, F1, false-implemented rate, Wilson intervals |
| E2 | per-operator breakdown | which policy catches which mutation |
| E3 | **identifier-ablation sweep**, rename 0–100% | degradation curves — the headline figure |
| E4 | counterfactual value-add | `cdc` against `cdc_counterfactual` |
| E5 | calibration | probability a claim is truly implemented, given `C = k` |
| E6 | scaling and runtime | elements, claims, evidence, seconds |

**Figures.** fig1 architecture; fig2 the worked dependent-evidence example; fig3 policy
comparison; fig4 identifier-ablation curves; fig5 calibration; fig6 per-operator recall.

## 10. Testing

Dependency-free, runnable as `python tests/test_corroborate.py`, and pytest-compatible.
The suite pins semantics, not implementation details:

1. Three name-derived pieces of evidence count as one witness, not three.
2. Provenance sharing is not transitive: `e1`–`e2` share a token, `e2`–`e3` share a file,
   yet `C = 2` because `e1` and `e3` are disjoint.
3. The witness set returned is exactly maximum and genuinely pairwise disjoint.
4. Counterfactual ablation demotes a name-only claim from `SUPPORTED` to `WEAK`.
5. A `NOMINAL` mutation is caught by `cdc_counterfactual` and missed by `hybrid`.
6. Claim extraction agrees between the Markdown and LaTeX frontends on equivalent input.
7. Gap scores aggregate correctly from claims to components to document.
8. Mutation labels round-trip: every injected mutation is recoverable from the manifest.

## 11. Honest limitations

Stated in the README and on the Conclusion slide, not buried:

- Ground truth is mutation-injected. The mutation operators encode our own assumptions
  about how implementations diverge from claims, and real divergence may not look like this.
- Channel independence is an assumption, not a proof. `DOC` and `NAME` are strongly
  correlated in practice, and provenance tagging only partly captures that.
- `BODY` analysis is shallow: a normalised operation vocabulary from the AST, not semantic
  understanding. It detects stubs reliably and weakened algorithms only sometimes.
- The default embedder is a lexical-semantic proxy, so the `embedding` and `hybrid`
  baselines are somewhat weaker than a neural implementation would be. Reported as such.
- Corpus scale is small. Wilson intervals are reported throughout, so a reader can see
  which differences the sample size actually resolves.
- Python only.

## 12. Commit convention

Conventional Commits, scoped to module names:

```
feat(corroborate): add counterfactual source ablation
feat(evidence): add IMPORT and CALL channels
test(corroborate): pin non-transitivity of provenance sharing
docs(readme): record E1 headline table
chore(corpus): vendor manifest and licences
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `build`.
Scopes: `model`, `codebase`, `claims`, `evidence`, `corroborate`, `scoring`, `policies`,
`mutate`, `corpus`, `experiments`, `figures`, `readme`, `report`, `slides`.

## 13. Deliverables

1. `cdc-trace/` — the working implementation, corpus, experiments, figures, tests, README.
2. `docs/report/` — draft report sections mapped to the BCSE497J template.
3. `docs/slides/` — slide-by-slide content for the 13-slide Review 2 template.
4. `docs/demo.md` — scripted walkthrough, exact commands, anticipated questions.
