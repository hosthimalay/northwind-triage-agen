# CloudServe Solutions — FDE Capstone

**Status (2026-11-21)** — 24 tests pass and the 80-ticket offline run reconciles to 80 audit records. SAM template validation passes. AWS deployment and live OpenAI calls are pending.

## What is implemented

Four-channel ingestion; supervised intent/urgency classification with numeric scores and alternatives; ranked article retrieval with verifiable IDs; deterministic policy routing; verifiable extractive citations; optional OpenAI evidence selection; output and privacy guardrails; per-ticket SQLite audit logs; unattended parameterised evaluation; measurable fairness slices; FastAPI demo; AWS SAM infrastructure sketch; pytest.

**Important:** The default generation mode is deterministic *extractive* synthesis. Set `--use-openai` in the batch harness to demonstrate genuine OpenAI-powered evidence selection. Without a valid key, this flag causes safe escalations. Neither retrieval nor training uses any validation labels; they are used only for metrics after predictions.

## Clean checkout — Python 3.11

```bash
cd cloudserve-capstone
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest tests/ -q
python -m cloudserve.evaluation --input data/validation_tickets.json --output evaluation/results
python -m uvicorn cloudserve.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the API demonstration. The evaluation command creates `results.jsonl`, `decisions.sqlite3` and `metrics.json`. The SQLite `decisions` table has one row per input for the run, and `decision_audit` holds the corresponding governance record. It can accept a hidden evaluation path; never hardcode ticket counts or labels.

**Data:** The official capstone `development_tickets.json`, `validation_tickets.json` and `documentation.json` must be in `data/`. They are included on this branch and are equal to the original assignment data after parsing. The validation labels are read only for metrics.

## How this maps to assessment A1–A12

- A1: clean checkout README, requirements and working directory.
- A2: `normalise_ticket`, test of four channels.
- A3: supervised logistic regression for intent and urgency; confidence and top alternatives.
- A4: `KnowledgeBase.search` returns ranked full-article passages and corpus IDs.
- A5: deterministic `CloudServeEngine.process` threshold and policy routing.
- A6: `_evidence_answer`, `validate_answer` with literal source excerpts and IDs.
- A7: pre-routing incident guardrail and output block on invalid citations/commitments.
- A8: SQLite `DecisionStore`, one row per ticket per run.
- A9: `cloudserve.evaluation --input ... --output ...`, arbitrary length input.
- A10: `metrics.json`, precision/recall by class, retrieval, FCR proxy, latency, governance and fairness.
- A11: safe escalation for bad input, model timeouts, no retrieval, and other failures.
- A12: `pytest tests/ -q`.

## FDE design choices and honest limits

- The 29 curated articles are the only answer authority; unreviewed personal snippets are excluded.
- Preserving complete resolution sections reduces chunk-boundary ambiguity. Retrieval combines word and character TF-IDF and re-ranks articles using a development-only intent-conditioned document prior. It is **lexical retrieval, not true neural semantic embeddings**. It must be compared against neural embeddings in a future experiment.
- Intent classification now uses character n-gram logistic regression (development grouped holdout 4-seed mean accuracy approximately 93.7%, versus 87.3% for the original word model). Logistic-regression probabilities are **not calibrated**. Improve calibration using development-only cross-validation before making confidence based automation claims.
- Automated answer rate is **not observed first-contact resolution**. Customer outcomes must be measured after deployment. Response latency in this harness is processing time, not customer-experienced wait.
- The four hard-block intents are `security_incident`, `compliance_request`, `feature_request`, `unclear_request`; keywords add an independent incident check.
- The AWS SAM template is an **optional demo sketch**, not an implemented production integration. Its Lambda container-image handler writes audit decisions to DynamoDB and fails closed if persistence is unavailable. This deployment has not yet been tested against a live AWS account. Keep the local evaluator as the authoritative grading implementation.
- Real Jira and Confluence integration, vector servers, React and Grafana are intentionally out of scope. A production architecture could add integrations behind the existing ingestion/retrieval interfaces after evaluation.

## Northwind reuse

The design follows Northwind's pre- and post-LLM guardrail and human-escalation pattern, but this implementation is new and ticket-specific. The Northwind source is maintained separately. No real Northwind or CloudServe secrets are required or committed.

## Data overlap audit and write-up

Run `python -m evaluation.grouped_audit` to inspect duplicate texts across splits and the grouped development holdout. The supplied validation set repeats 62 development ticket bodies; the excellent observed validation intent score is optimistic. The report in `deliverables/` explains the leakage limitation and the weak urgency holdout result. The five workbooks are working drafts requiring your review and an honest, separately filled effort log.

## GitHub Actions

When this project is placed inside the existing Northwind repository as `cloudserve-capstone/`, copy `.github/workflows/cloudserve-test.yml` to the **repository root** `.github/workflows/` so GitHub Actions recognises it. The CI job skips evaluation when official datasets have not been uploaded and explicitly prints that the run was skipped; it must not be represented as a passed assessment run.

## 2026-11-16 offline engineering revision

We improved the intent representation and retrieval after seeing that two
phrasings of the same rate-limit question triggered different decisions.
The development-only evidence and four-split experiment are in
[`docs/ENGINEERING_EXPERIMENT.md`](docs/ENGINEERING_EXPERIMENT.md).

A fresh unattended local **validation** run after those design decisions:

| Metric | Initial offline baseline | Revised offline version |
|---|---:|---:|
| Tickets processed | 80 | 80 |
| Automatic drafts | 56 | 65 |
| Escalations | 24 | 15 |
| Retrieved relevant doc (top 3) | 83.0% | 92.5% |
| Correct citations among evaluated drafts | 95.1% | 93.8% |
| Prohibited tickets auto-answered | 0/14 | 0/14 |

**Important trade-off:** citation accuracy is below the aspirational 95%
target. The 65 automatic drafts are **not** demonstrated first-contact
resolutions. The validation texts have substantial development overlap
(62/80 bodies), so do not cite validation intent accuracy as generalisation.
Urgency remains advisory only.

### Simple local API demonstration

`POST /tickets` accepts a JSON body such as:

```json
{
  "ticket_id": "DEMO-003",
  "channel": "chat",
  "subject": "HTTP 429 Too Many Requests API rate limit exceeded",
  "body": "Requests exceed rate limit, please explain quota and backoff."
}
```

Look at `route`, `reason`, `citations`, `guardrails` and `generator`.
`generator: deterministic_extract` means no OpenAI call occurred.

### Optional OpenAI locally (never commit secrets)

Install `requirements-openai.txt`, set `OPENAI_API_KEY` in your
PowerShell **session** and set `USE_OPENAI=1` before restarting the API.
An actual successful call should report
`generator: openai_evidence_selection`. This selects exact source excerpts;
it does **not** generate a free-form answer. Credentials are excluded
from repositories. Known emails, API-key patterns and card-like strings
are redacted from prompts, but this is not a comprehensive PII solution.

### AWS Tokyo demonstration (still pending authorised deployment)

A Docker-capable machine with SAM CLI and permission to deploy
CloudFormation, ECR, IAM, Lambda, API Gateway, DynamoDB and CloudWatch is
required. The SAM template uses a container image because scientific
Python dependencies can be large; it does not publish the evaluation
labels in the runtime image.

1. Create an AWS Secrets Manager secret in `ap-northeast-1` containing
   the API key (plaintext or `{"OPENAI_API_KEY":"..."}`). Record its
   **ARN**, not its plaintext value. Reuse an existing permitted secret
   if one is already managed in your AWS account.
2. From `cloudserve-capstone/`:

   ```bash
   sam validate --template-file infra/template.yaml
   sam build --template-file infra/template.yaml
   sam deploy --guided --stack-name cloudserve-capstone --region ap-northeast-1 \
      --parameter-overrides UseOpenAI=1 OpenAISecretArn=<YOUR_SECRET_ARN>
   ```

3. Authenticate API calls with AWS Signature V4 (the HTTP API is
   IAM-protected). Verify `/health`, a normal ticket, a security
   escalation, the DynamoDB audit table and CloudWatch logs.
4. Never claim AWS deployment or live OpenAI functionality until a real
   response and cloud resource identifiers have been verified.

For an offline AWS adapter test without AWS credentials, run the
`test_lambda_handler_local_adapter_with_mocked_store` and
`test_lambda_fails_closed_if_audit_write_fails` tests.
