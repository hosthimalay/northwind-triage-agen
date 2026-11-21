# Submission status

## 21 November 2026 verification and follow-up

- The current suite has 25 tests. The additional API test confirms pause, resume, escalation if paused during generation, audit persistence and metrics exposition.
- The local Prometheus configuration and six-panel Grafana dashboard are in `monitoring/`. The batch grading command has no running monitoring dependencies.
- The fairness report now includes ticket length. In this run the short slice matched 132/138 references. The long slice matched 3/6 and contains only two tickets, which is too small for a stable comparison.
- Additional grouped development experiments tested alternate relevance thresholds, title weights and similar historical tickets. The baseline thresholds remain in use. See `ENGINEERING_EXPERIMENT.md`.

- 24 tests passed. The local FastAPI application was exercised through its ASGI interface for all four channels and the compromise guardrail.
- Official validation processed and logged 80 tickets. It produced 65 automatic drafts and 15 escalations. All 14 reference-prohibited tickets escalated.
- Top-three retrieval matched the reference on 49 of 53 labelled tickets. All 195 emitted citations resolved to retrieved source text. Of the 144 citations with reference document labels, 135 matched (93.75%, below the 95% target).
- The intent-conditioned article boost increased from 0.15 to 0.25 after a grouped development comparison. Across four overlapping splits, top-source matches increased from 296/334 to 302/334. Top-three recall and the official validation citation figure were unchanged. A hard prior filter lost correct sources on development data and was discarded.
- Confidence bands show large gaps. Validation is optimistic because 62 of 80 ticket bodies overlap development. Urgency remains advisory. Citation-match spreads across the labelled slices were 9.5 points by tier, 12.5 by region and 7.5 by language fluency. These are sample estimates and do not clear the five-point governance target.
- SAM template validation passed after enabling the HTTP API IAM authorizer. The image build could not reach Docker Desktop's Linux engine. A credential-missing OpenAI run escalated safely. AWS deployment and a live OpenAI response remain pending.
- The assessor's hidden set, two-person hallucination review, customer outcomes, completed submission draft and recorded video remain pending.

## Earlier draft inventory

- Python source: local 22 tests pass; revised 80-ticket offline evaluation complete.
- Metrics and grouped development experiment are committed in evaluation/.
- Five workbooks: populated draft; PRD revision and prompt-library appendices updated.
- Report: 23-page original baseline plus explicit revised-results notice and addendum (draft).
- Effort log: student must enter genuine hours; no invented dates/hours.
- Video: NOT recorded; student must demonstrate actual running system.
- OpenAI API: SDK integration unit-tested with mocks; NO verified live call.
- AWS: image-based SAM template, adapter unit tests; NO deployed resources verified.
- Validation caveats: 62/80 exact body overlap with development; revised citation accuracy below 95%.

The grading gate is a clean checkout and unattended full evaluation run.
Do not substitute cloud deployment for that evidence.
