# CloudServe FDE - Development-only model comparison (2026-11-16)

## Hypothesis
Ticket phrases are noisy and can contain typos. Character n-grams should
be less sensitive to wording than word-bigram TF-IDF. We also tested
combining word/character retrieval without adding a vector database.

## Method (no validation labels used for model selection)
- Dataset: 500 labelled development tickets.
- Group by normalised **ticket body** before train/holdout split; this limits
  exact-body leakage within each split.
- GroupShuffleSplit test_size 0.22, seeds 42, 17, 77, 110.
- Hold out original 80 validation tickets from the decision procedure.
- Compare balanced logistic regression with word (1,2) TF-IDF versus
  character-boundary (3,5) TF-IDF.

| Seed | Held-out n | Word intent accuracy | Character intent accuracy |
|---|---:|---:|---:|
| 42 | 108 | 87.04% | 94.44% |
| 17 | 96 | 91.67% | 97.92% |
| 77 | 95 | 89.47% | 93.68% |
| 110 | 132 | 81.06% | 88.64% |

Mean accuracies across the four **overlapping** splits: 87.31% versus 93.67%.
These splits are not independent and this is not a confidence interval.

One grouped development split (seed 42) on 88 tickets with known documents:
word-only top-3 retrieval: 94.32%; combined word/character top-3: 95.45%.
That is a small directional difference, not a production-scale proof.

## Document prior experiment
We then tested an intent-conditioned document prior, using only historical
development labels to break ties between high-scoring articles. The prior
boost is small (0.15 times within-intent document frequency) and can only
reorder passages that already pass the raw relevance filter.

| Seed | Held-out tickets with doc labels | Hybrid top-1 | With prior top-1 |
|---|---:|---:|---:|
| 42 | 88 | 86.36% | 93.18% |
| 17 | 73 | 87.67% | 91.78% |
| 77 | 62 | 85.48% | 93.55% |

This is a learning-to-rerank baseline based on supervised historical ticket
resolution metadata, NOT a neural reranker or a live Confluence index.
It must not override a raw relevance threshold.

## Decision
Adopt character n-grams for **intent**, hybrid lexical retrieval, and
a limited documented historical article prior.
Keep urgency as an advisory prediction; its older grouped-holdout accuracy
was only around 48%. Retain existing policy hard blocks and automatic
answer eligibility checks, tightening the provisional intent threshold from
0.10 to 0.15 based on development-only selective precision. Do NOT call the uncalibrated logistic-regression
probabilities calibrated confidence, and do not lower the routing threshold
solely to increase automation.

## Limitations and next steps
- Duplicate or near-duplicate tickets may remain across some groups.
- Some validation ticket texts overlap development; do not claim that a high
  validation score proves out-of-distribution generalisation.
- Real human support feedback is needed for first-contact resolution, fairness
  and hallucination estimates. Automation is only a proxy.
- Live OpenAI/AWS deployment is not verified by these offline experiments.

Reproduce via `python -m evaluation.classifier_comparison`.
