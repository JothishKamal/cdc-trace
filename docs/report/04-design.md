# Design

## System Architecture

Pipeline from documents and code to gap scores. Module numbers match the specification (100–800).

```
        claims document                       code archive
       (Markdown / LaTeX)                     (Python repo)
              |                                     |
      [300] claim extraction              [200] code extraction
      rule-based default,                 AST inventory, call graph,
      LLM backend (cached)                routes, schema, imports, tests
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

```mermaid
flowchart LR
  Doc[Claims document] --> M300[300 claims]
  Code[Python archive] --> M200[200 codebase]
  M300 --> M400[400 evidence]
  M200 --> M400
  M400 --> M500[500 corroborate]
  M500 --> M600[600 scoring / policies]
  M700[700 mutate] --> M800[800 experiments]
  M600 --> M800
```

Set-valued provenance is load-bearing. If each piece of evidence carried a single channel tag, “channel-disjoint” would collapse into counting distinct channels and the maximum independent set would be decoration. Connected components are the wrong tool: `e1` may share a token with `e2` and `e2` share a file with `e3` while `e1` and `e3` remain disjoint.

## Data Flow

```mermaid
flowchart TD
  MD[doc.md / doc.tex] --> Claims[Claim list]
  PY[code/*.py] --> Elements[CodeElement inventory]
  Claims --> Gather[gather seven channels]
  Elements --> Gather
  Gather --> Ev[Evidence with provenance sets]
  Ev --> C[C = MIS pairwise-disjoint]
  Ev --> Ablate[ablate each source, recompute C]
  C --> Verd[SUPPORTED / WEAK / UNSUPPORTED]
  Ablate --> Verd
  Verd --> Gap[component and document gap scores]
  Mut[mutation copy of tree] --> Elements
```

`strength` governs emission only. It plays no part in disjointness and no part in `C(claim)`. Making the count strength-weighted would reintroduce the rescaling the method argues cannot fix correlated agreement.

## Use Case

```mermaid
flowchart LR
  Analyst((Analyst)) --> UC1[Extract claims and code]
  Analyst --> UC2[Score a document]
  Analyst --> UC3[Compare policies on mutations]
  Analyst --> UC4[Print E1/E2/E4 tables]
  Analyst --> UC5[Render figures]
  UC3 --> UC4
```

Primary actor: an analyst with a claims document and a Python tree. The system extracts artefacts, emits evidence, reports `C`, worst-case ablated `C`, and a verdict per claim, then a gap score. Experiments apply operators on a copy and score policies against labels known by construction. The system does not grade, detect plagiarism, or call a live LLM.

## Class Diagram

```mermaid
classDiagram
  class Claim {
    cid component text kind
    terms implied_libs section
  }
  class CodeElement {
    uid kind name path lineno
    doc imports calls body_ops
    is_stub reachable
  }
  class Evidence {
    claim element channel
    provenance strength
  }
  class ClaimResult {
    cid component verdict
    c worst_c worst_source
    n_evidence capped
  }
  class GapReport {
    results by_component gap_score
  }
  class Mutation {
    operator target_uid target_name
    path claim_cid
  }
  Claim --> Evidence
  CodeElement --> Evidence
  ClaimResult --> GapReport
  Mutation --> Claim
```

All of `Claim`, `CodeElement`, and `Evidence` are frozen. Provenance is `FrozenSet[str]`.

## Sequence Diagram

```mermaid
sequenceDiagram
  participant A as Analyst
  participant Cl as 300 claims
  participant Cb as 200 codebase
  participant Ev as 400 evidence
  participant Co as 500 corroborate
  participant Sc as 600 scoring
  A->>Cl: extract_claims(doc, md|tex)
  A->>Cb: extract_codebase(code_dir)
  A->>Ev: gather(claim, elements)
  Ev-->>Sc: Evidence list
  Sc->>Co: corroboration / counterfactual_worst
  Co-->>Sc: C, worst C, source
  Sc-->>A: ClaimResult, GapReport
```

For evaluation, module 700 copies the tree, applies an operator, and records the targeted claim. Module 800 scores each policy on the gap class (not implemented) and writes `results/results.json`.
