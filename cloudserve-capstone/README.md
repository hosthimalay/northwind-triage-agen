# CloudServe Solutions — FDE Capstone

**Status:** locally testable baseline; AWS deployment and live OpenAI calls are NOT verified. Built as a separate extension of the Northwind triage case study.

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

Open `http://127.0.0.1:8000/docs` for the API demonstration. The evaluation command creates `results.jsonl`, `decisions.sqlite3` and `metrics.json`. It can accept a hidden evaluation path; never hardcode ticket counts or labels.

**Data:** The official capstone `development_tickets.json`, `validation_tickets.json` and `documentation.json` must be in `data/`. They are included in the downloadable project package; if only the source directory is copied to GitHub without the data, import these files from the official pack before running. Never train on validation labels.

## OpenAI option

```bash
# Export through your shell or a secrets manager. Never commit a key.
export OPENAI_API_KEY='YOUR_KEY_HERE'
python -m cloudserve.evaluation --input data/validation_tickets.json --output evaluation/openai-results --use-openai
```

On PowerShell, use `$env:OPENAI_API_KEY = 'YOUR_KEY_HERE'`. This incurs API costs; use a small development subset before the full run. The model is constrained to selecting exact, pre-supplied document excerpts. Python verifies each quoted excerpt and builds the customer-facing draft; a model cannot override escalation rules.

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
- Preserving complete resolution sections reduces chunk-boundary ambiguity. Full-article ranking uses lexical TF-IDF: a **lightweight baseline**, not true semantic neural embeddings. It must be compared against neural embeddings in a future experiment.
- Logistic-regression probability is **not guaranteed calibrated**. Improve calibration using development-only cross-validation before making confidence based automation claims.
- Automated answer rate is **not observed first-contact resolution**. Customer outcomes must be measured after deployment. Response latency in this harness is processing time, not customer-experienced wait.
- The four hard-block intents are `security_incident`, `compliance_request`, `feature_request`, `unclear_request`; keywords add an independent incident check.
- The AWS SAM template is an **optional demo sketch**, not an implemented production integration. Its Lambda handler writes audit decisions to DynamoDB and fails closed if persistence is unavailable, but this AWS deployment has not yet been tested. Keep the local evaluator as the authoritative grading implementation.
- Real Jira and Confluence integration, vector servers, React and Grafana are intentionally out of scope. A production architecture could add integrations behind the existing ingestion/retrieval interfaces after evaluation.

## Northwind reuse

The design follows Northwind's pre- and post-LLM guardrail and human-escalation pattern, but this implementation is new and ticket-specific. The Northwind source is maintained separately. No real Northwind or CloudServe secrets are required or committed.

## Data overlap audit and write-up

Run `python -m evaluation.grouped_audit` to inspect duplicate texts across splits and the grouped development holdout. The supplied validation set repeats 62 development ticket bodies; the excellent observed validation intent score is optimistic. The report in `deliverables/` explains the leakage limitation and the weak urgency holdout result. The five workbooks are working drafts requiring your review and an honest, separately filled effort log.

## GitHub Actions

When this project is placed inside the existing Northwind repository as `cloudserve-capstone/`, copy `.github/workflows/cloudserve-test.yml` to the **repository root** `.github/workflows/` so GitHub Actions recognises it. The CI job skips evaluation when official datasets have not been uploaded and explicitly prints that the run was skipped; it must not be represented as a passed assessment run.

## Optional AWS SAM (not yet deployed)

After configuring an AWS account/role, AWS SAM CLI and the Tokyo region:

```bash
cd cloudserve-capstone
sam build --template-file infra/template.yaml
sam deploy --guided --region ap-northeast-1
```

The API uses IAM authentication, so calling it requires an authenticated Signature V4 client. Verify the deployed function and DynamoDB audit table in the AWS Console before claiming the cloud test passed. No AWS resource has been created in this project session.
