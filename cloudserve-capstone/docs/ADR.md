# CloudServe Capstone — Architecture Decision Register

**ADR-001 Problem framing** — Solve safe support resolution rather than deploying a chatbot. Stakeholder evidence from Sofia, Ines and Daniel indicates searching verified answers and missing escalation context are dominant bottlenecks. Alternative: general customer-facing chat; rejected because it does not define truth or safe routing.

**ADR-002 Approved documentation** — Use only the 29 supplied curated support articles. Alternative: private agent snippets; rejected because Ines says those are unreviewed and may be stale. Future Confluence integration is conditional on verified access and document versioning.

**ADR-003 Classification** — TF-IDF + logistic regression, with intent/urgency scores and alternatives, because 500 labelled development tickets are supplied. Alternative: training a PyTorch network or one-shot LLM classification; rejected for the baseline due limited data, cost and opacity. Grouped dev holdout: 87.0% intent, 48.1% urgency; consequently do NOT auto-prioritise by urgency.

**ADR-004 Retrieval** — Article-level TF-IDF for 29 small articles with real doc identifiers. Alternative: Chroma/vector server + MiniLM embeddings; deferred until a controlled measured improvement, because a dedicated vector service adds setup. Validation top-3 expected doc hit: 83.0%, below aspirational 90%; this is an explicit weakness.

**ADR-005 Routing** — Hard block prohibited intents and compromise/financial/legal patterns before checking classifier score and document similarity. Alternative: model-chosen route; rejected because unsafe outcomes cannot be argued away by generative text. Prototype thresholds: classifier .10, retrieval .12; NOT statistically calibrated production values.

**ADR-006 Generation and validation** — Deterministic source-extractive baseline with optional OpenAI selector of verbatim evidence. Python validates all citations and blocks secret/financial commitment patterns; OpenAI may not override the decision. Local default makes clean-checkout assessment work without API costs. Live OpenAI mode unverified without secret and provider access.

**ADR-007 Persistence** — SQLite for grader and DynamoDB for optional AWS Lambda. Reason: clean-run portability and cloud audit durability. Fail closed if cloud audit persistence fails. No production retention policy yet.

**ADR-008 Deployment** — Build and evaluate locally, then optional AWS SAM HTTP API + Lambda + DynamoDB in ap-northeast-1 with IAM authentication and CloudWatch logging. Alternative: complete React/Jira/Confluence enterprise rollout; rejected as unnecessary to A1–A12.

**ADR-009 Monitoring** — Built-in CloudWatch for optional AWS instead of Prometheus/Grafana. Locally, JSON metrics and SQLite audit provide the assessor the required signals without extra services.

**ADR-010 Measurement** — Separate automation rate from actual first-contact resolution, which requires post-deployment customer outcomes. Group text-identical tickets in development holdout: 62/80 validation bodies overlap dev; 100% validation intent accuracy is not a credible estimate of fresh-language generalisation.

**Reuse attribution:** Northwind Returns & Warranty Triage Agent provided the design pattern for pre/post Python guardrails and transparent evidence traces. The CloudServe code was newly generated with AI assistance. Student should review, test and declare tools used before assessment submission.


## ADR-011: Development-only representation and retrieval revision (2026-11-16)

The first Swagger demo exposed a threshold-sensitive rate-limit classification.
Before changing the model we compared four **grouped development** holdout
splits: character n-grams improved mean intent accuracy from ~87.3% to
~93.7%. A hybrid word/character corpus and small intent-conditioned
article-frequency prior improved top-1 document accuracy in three grouped
development splits; the prior never overrides raw relevance filtering.
The classifier threshold moved from .10 to .15 based on development-only
selective prediction. After revision, validation top-3 document hit rose
from 83.0% to 92.5%, but citation accuracy decreased from 95.1% to
93.8%. This is **not unequivocal improvement**; precision needs more work.
No retriever training uses the supplied validation reference labels.

## ADR-012: Lambda container and secret handling

Package with AWS SAM as an OCI container image to make scientific Python
package-size constraints explicit; use Secrets Manager GetSecretValue
through a narrowly scoped role for the optional live OpenAI path.
The REST endpoint requires AWS_IAM authentication and logs only hashed
ticket input plus decision metadata. The AWS deployment is NOT confirmed.
