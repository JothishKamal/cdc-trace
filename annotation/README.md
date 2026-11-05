# Claim annotation kit

Measures how well the rule-based claim extractor works (review items M1, M2 and D5).
It needs people to label sentences; nothing here has been labelled yet.

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
