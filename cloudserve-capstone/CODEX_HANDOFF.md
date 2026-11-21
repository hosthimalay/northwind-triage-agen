# Codex handoff — CloudServe FDE capstone

**Status:** 21 November 2026. Continue this existing FDE assignment, do not start a new product.

## Repository and scope
- Project: `cloudserve-capstone/` on branch `feat/cloudserve-fde-capstone`.
- Parent repo: `hosthimalay/northwind-triage-agen`; original Northwind remains on `main`.
- Draft PR: https://github.com/hosthimalay/northwind-triage-agen/pull/1
- Read `README.md`, `docs/SUBMISSION_STATUS.md`, `docs/ADR.md`, `docs/ENGINEERING_EXPERIMENT.md`, `docs/AI_USE_DECLARATION.md` and `docs/VIDEO_SCRIPT.md` from this project directory.
- Obtain the **original** `FDE_Capstone_Complete-20260821T084330Z-1-001.zip` and separate `CloudServe_FDE_Capstone_REVISED_DRAFT.zip` from the student. They contain authoritative instructor guidance and draft workbooks/report; do not assume they are available in the GitHub branch.

## Baseline facts
- Revised local source passed 22 tests; GitHub Actions ran successfully (20 Nov).
- Offline 80-ticket validation: 80 processed/logged, 65 auto-drafts, 15 escalations, 0 automatic answers across 14 prohibited tickets.
- Top-3 retrieval hit ~92.45%; citation correctness among evaluated drafts ~93.75%, below 95% target.
- Development-only grouped splits: mean intent accuracy ~93.7% for character TF-IDF vs ~87.3% word baseline. Urgency precision remains weak (~43.9% macro).
- 62/80 validation bodies overlap the training corpus. 100% validation intent accuracy is not evidence of novel-language generalization.
- Auto-response is a proxy; actual customer FCR has not been measured.
- OpenAI is optional evidence-selection only: default `generator=deterministic_extract` does NOT call GPT. OpenAI mocked tests exist; live model call has not been verified.
- AWS SAM image template is a scaffold for Tokyo region (`ap-northeast-1`) with IAM-protected API Gateway, Lambda, DynamoDB, Secrets Manager and CloudWatch. No live AWS deployment or successful endpoint call has been verified.

## Next steps in grading priority
1. Read the exact instructor Build Specification and check A1–A12 end-to-end from a clean checkout, especially unattended evaluation.
2. Inspect and correct citation misses without compromising deterministic guardrails; document urgency limitations and calibration.
3. Make one **real** OpenAI call securely with the user's authorized credentials; capture success/fallback, latency and cost. Never expose or commit API keys.
4. If approved AWS access exists, validate/build/deploy/test SAM resources in Tokyo and record real evidence. Keep the local grading harness independent of AWS.
5. Reconcile the draft PDF and five workbooks against current code/results, review AI-use declaration, request genuine effort-hours, and prepare an 18–22-minute student video demonstration.
6. Prioritize demonstrable rubric compliance; **do not** add Jira/Confluence integration, React, Prometheus/Grafana or a new SaaS unless the exact assignment justifies it.

## Local commands
```powershell
cd cloudserve-capstone
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest tests/ -q
python -m cloudserve.evaluation --input data/validation_tickets.json --output evaluation/results
python -m uvicorn cloudserve.api:app --host 127.0.0.1 --port 8000
```

The instructor's original printed deadline was extended per the student; ask them for the new deadline only if the submission schedule depends on it. Keep explanations educational: the student needs to understand and personally demonstrate every major component.
