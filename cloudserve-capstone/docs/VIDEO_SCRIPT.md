# Student video demonstration plan (18–22 minutes)

**Not recorded yet. The student must be on camera for opening and closing, and demonstrate the actual running system at least seven minutes.**

0:00–2:00 — Introduce CloudServe's fictional support problem, 500+ weekly tickets, first-response delay and why chatbot is not the outcome.

2:00–5:00 — Discovery: five stakeholders, 71.4% docs-answerable, 17.4% hard-prohibited, and 43.8% historical sample FCR. Explain knowledge findability and escalation quality.

5:00–7:00 — Diagram the six-stage pipeline, show `core.py`, demonstrate that routing and guardrails are enforced in Python rather than a prompt.

7:00–9:00 — Launch `python -m uvicorn cloudserve.api:app --port 8000` and open `/docs`. Send a normal API rate-limit question from `chat` and follow its real `DOC-API-001` citations. Do not claim a live OpenAI call unless `USE_OPENAI` actually enabled and a real call succeeded.

9:00–11:00 — Send a suspected compromise ticket. Show `escalate`, policy reason and no sent answer. Also run an unsupported refund commitment through `validate_answer` or automated test to show an actual block.

11:00–14:00 — Run `python -m cloudserve.evaluation --input data/validation_tickets.json --output evaluation/demo` uninterrupted; open results JSONL and SQLite DB, reconcile exactly 80 tickets, display metrics. Run `python -m pytest tests/ -q`.

14:00–17:00 — Explain 56 auto drafts, 24 escalations, 83.0% retrieval hit, 95.1% eligible citation accuracy, zero unsafe auto sends. Crucially, 70% is NOT measured FCR. Run `python -m evaluation.grouped_audit` and explain 62/80 body overlap and 48% urgency grouped holdout.

17:00–18:00 — Governance: privacy, citations, no model override of deterministic rules, safe outage path and fairness group gaps.

18:00–20:00 — PRD revision, architecture decisions, limitations (OpenAI and AWS unverified unless separately demonstrated), future Jira/Confluence integration and human pilot. On-camera close.

## Recording checklist

- Screen capture at 1080p or better; enlarge terminal fonts; ensure audio readable.
- Live demo must show normal answer, escalation, guardrail blocked and full unattended batch.
- Use only real results. Record actual API costs/times if OpenAI enabled.
- Upload the actual video or add approved link under `01_Video` before submission.
