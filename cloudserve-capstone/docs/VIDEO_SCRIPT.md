# Student video demonstration plan (18–22 minutes)

**Not recorded yet. The student must be on camera for opening and closing, and demonstrate the actual running system at least seven minutes.**

0:00–2:00 — Introduce CloudServe's fictional support problem, 500+ weekly tickets, first-response delay and why chatbot is not the outcome.

2:00–5:00 — Discovery: five stakeholders, 71.4% docs-answerable, 17.4% hard-prohibited, and 43.8% historical sample FCR. Explain knowledge findability and escalation quality.

5:00–7:00 — Diagram the six-stage pipeline, show `core.py`, demonstrate that routing and guardrails are enforced in Python rather than a prompt.

7:00–9:00 — Launch `python -m uvicorn cloudserve.api:app --port 8000` and open `/docs`. Send a normal API rate-limit question from `chat` and follow its real `DOC-API-001` citations. Do not claim a live OpenAI call unless `USE_OPENAI` actually enabled and a real call succeeded.

9:00–11:00 — Send a suspected compromise ticket. Show `escalate`, policy reason and no sent answer. Also run an unsupported refund commitment through `validate_answer` or automated test to show an actual block.

11:00–14:00 — Run `python -m cloudserve.evaluation --input data/validation_tickets.json --output evaluation/demo` uninterrupted; open results JSONL and SQLite DB, reconcile exactly 80 tickets, display metrics. Run `python -m pytest tests/ -q`.

14:00–17:00 — Explain the 21 November run: 65 automatic drafts, 15 escalations, 49/53 labelled top-three retrieval hits, and 135/144 per-citation reference matches (93.75%). All 195 emitted excerpts were checked against the retrieved articles. The reference-match target remains below 95%. Explain the difference between quoting an article accurately and choosing the right article for the ticket. Draft rate (81.25%) is a proxy for automation. Customer first-contact resolution requires closure data. Mention the 62/80 validation body overlap and show the calibration bands and urgency limitations.

17:00–18:00 — Governance: privacy, citations, no model override of deterministic rules, safe outage path and fairness group gaps.

18:00–20:00 — PRD revision, architecture decisions, limitations (OpenAI and AWS unverified unless separately demonstrated), future Jira/Confluence integration and human pilot. On-camera close.

## Recording checklist

- Screen capture at 1080p or better; enlarge terminal fonts; ensure audio readable.
- Live demo must show normal answer, escalation, guardrail blocked and full unattended batch.
- Use only real results. Record actual API costs/times if OpenAI enabled.
- Upload the actual video or add approved link under `01_Video` before submission.


Demonstrate the new grouped-holdout experiment with `python -m evaluation.classifier_comparison`. Describe that the model is character TF-IDF, not a trained deep network, and the retrieval is lexical rather than neural embeddings. Do not describe a mocked OpenAI unit test as a live model request.
