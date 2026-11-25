# Claim annotation kit

Measures how well the rule-based claim extractor works (review items M1, M2 and D5).
`sentences.csv` is now labelled by two annotators outside the team (columns `_a` and `_b`);
`python annotation/annotate.py score annotation/sentences.csv > results/annotation.json`
reproduces the numbers in Section 3.1 of the paper. `sentences_provisional.csv` holds the
earlier LLM labels, kept for comparison only.

1. `python annotation/annotate.py template` writes `annotation/sentences.csv`: every
   sentence of the six corpus documents (123 sentences, 80 of them extracted as claims).
   Pass document paths to annotate other reports instead, for example de-identified
   student submissions.
2. Two annotators who did not write the documents each fill their own columns
   (`_a` and `_b`) without seeing the `extracted` column:
   - `is_claim`: 1 if the sentence states something the code does or contains
   - `completed`: 1 if it describes finished work, 0 for plans or requirements
   - `component`: the component it is about; leave blank if the heading is right
3. `python annotation/annotate.py score annotation/sentences.csv` prints precision,
   recall and F1 of extraction (gold = `is_claim` and `completed`), the accuracy of
   heading-based component association, and Cohen's kappa between the annotators.

## README annotation (the nine PyPI libraries)

The same procedure, applied to the READMEs of the independent corpus, measures the extractor's
precision and recall on documentation the team did not write. The files are in `readmes/`:

- `readme_sentences.csv`: every sentence of the nine READMEs (1,032 sentences, 145 of them
  extracted as claims), with the extractor's output. Do not give this file to the annotators.
- `readme_sheet_A.csv` and `readme_sheet_B.csv`: the same sentences without the extractor's
  output, one sheet per annotator, now filled in by the same two annotators and merged into
  `readme_sentences.csv`. Badge lines and code fragments appear as sentences
  because the extractor sees them; mark them 0.

Each annotator fills `is_claim`, `completed` and `component` in their own sheet, using the rules
above and without seeing the other sheet. Then:

    python annotation/annotate.py merge annotation/readmes/readme
    python annotation/annotate.py score annotation/readmes/readme_sentences.csv > results/annotation_readme.json

Result: the annotators agree on 95.6% of sentences (kappa 0.90); against annotator A the
extractor's precision is 0.47 and recall 0.21 (`results/annotation_readme.json`).
`python experiments/readme_verdicts.py` splits the tool's claim verdicts by these labels
(`results/readme_verdicts.json`).

`sheets` regenerates blank files from scratch (this overwrites the filled sheets):

    python annotation/annotate.py sheets annotation/readmes/readme corpus_ext/*/doc.md
