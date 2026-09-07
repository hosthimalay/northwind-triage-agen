# POC — Retrieval + One Grounded LLM Call

Proves the core idea: given a claim, retrieve the relevant policy text and
make one LLM call that decides approve/deny/escalate, grounded only in what
was retrieved. No guardrails, state, or trace here on purpose — that's what
the MVP (`../console/`) adds.

```bash
pip install openai
export OPENAI_API_KEY="sk-..."
python poc_triage.py --all          # all 8 sample claims
python poc_triage.py claim-02       # a specific claim
```

`return_policy_kb.json` and `sample_claims.json` must stay in this same
folder — the script reads them from disk at runtime.
