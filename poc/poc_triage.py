"""
poc_triage.py — Part 3 POC: retrieve policy text, make one grounded LLM
call, decide approve/deny/escalate. No guardrails/state/trace here on
purpose — that's Part 4.

Uses the OpenAI API (this version — an Anthropic-API version exists too).

    export OPENAI_API_KEY="sk-..."
    pip install openai
    python poc_triage.py                     # 4 representative claims
    python poc_triage.py claim-02 claim-05    # specific ids
    python poc_triage.py --all                # all 8

No API key in the sandbox this was written in, so this exact run hasn't
produced real output yet — run it with your own key to capture that.
"""

import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles often default to cp932/cp1252

HERE = Path(__file__).parent
MODEL = "gpt-5.5"  # swap for "gpt-4o" if your account doesn't have gpt-5.5 access
DEFAULT_IDS = ["claim-01", "claim-03", "claim-04", "claim-06"]

STOPWORDS = {"the", "and", "this", "that", "for", "are", "with", "from", "was",
             "were", "has", "have", "had", "not", "but", "you", "your", "our",
             "its", "been", "just", "about", "dont", "don", "like", "want"}

# domain terms that should outweigh a bare keyword-overlap score
BOOSTS = [
    ("pol-003", r"clearance|final sale|discount"),
    ("pol-006", r"wrong (item|color|backpack|size)|sent me"),
    ("pol-007", r"exchange|fit|size|tags"),
    ("pol-005", r"shipping|transit|broken (pole|zipper)|unbox"),
    ("pol-002", r"defect|broken|manufactur"),
]


def tokenize(text):
    return [w for w in re.findall(r"[a-z]+", text.lower())
            if len(w) > 2 and w not in STOPWORDS]


def retrieve_policies(claim, policies, top_n=2):
    """Keyword-overlap retrieval — plenty at 8 documents, no vector DB needed."""
    claim_tokens = set(tokenize(claim["claim_text"]))
    text = claim["claim_text"].lower()
    scored = []
    for pol in policies:
        overlap = sum(1 for t in tokenize(pol["title"] + " " + pol["category"] + " " + pol["policy_text"])
                       if t in claim_tokens)
        boost = next((4 for pid, pat in BOOSTS if pol["id"] == pid and re.search(pat, text)), 0)
        scored.append({**pol, "score": overlap + boost})
    scored.sort(key=lambda p: p["score"], reverse=True)
    return [p for p in scored[:top_n] if p["score"] > 0]


def decide(claim, retrieved):
    """The one LLM call: decide approve/deny/escalate, grounded only in retrieved text."""
    from openai import OpenAI  # pip install openai
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit('OPENAI_API_KEY not set. Run: export OPENAI_API_KEY="sk-..."')

    policy_block = "\n\n".join(f"[{p['id']}] {p['title']}: {p['policy_text']}" for p in retrieved) \
        or "(no policy article matched this claim)"
    system = (
        "You are a returns/warranty decision agent for Northwind Outdoor Gear. Decide "
        "approve, deny, or escalate, grounded ONLY in the policy text given — never invent "
        "policy. If the text doesn't clearly cover the situation, escalate rather than guess. "
        'Respond with ONLY this JSON, no markdown fences: {"decision":"approve|deny|escalate",'
        '"confidence":0.0-1.0,"reason":"1-2 sentences citing the policy id"}'
    )
    user = (f"RETRIEVED POLICY TEXT:\n{policy_block}\n\nCLAIM:\nid: {claim['id']}\n"
            f"item_value_usd: {claim['item_value_usd']}\ndays_since_delivery: {claim['days_since_delivery']}\n"
            f"prior_claims_90d: {claim['prior_claims_90d']}\ncustomer_text: \"{claim['claim_text']}\"")

    resp = OpenAI(api_key=api_key).chat.completions.create(
        model=MODEL, max_completion_tokens=300,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    raw = re.sub(r"^```json|```$", "", resp.choices[0].message.content.strip()).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"decision": "escalate", "confidence": 0.0,
                "reason": f"Could not parse model output — escalating rather than guessing. Raw: {raw!r}"}


def run(claim_ids, policies, claims_by_id):
    for cid in claim_ids:
        claim = claims_by_id.get(cid)
        if not claim:
            print(f"!! unknown claim id: {cid}")
            continue
        retrieved = retrieve_policies(claim, policies)
        result = decide(claim, retrieved)
        print(f"\n{claim['id']} — ${claim['item_value_usd']}, {claim['days_since_delivery']}d, "
              f"{claim['prior_claims_90d']} prior claims")
        print(f'  "{claim["claim_text"]}"')
        print(f"  retrieved: {', '.join(p['id'] for p in retrieved) or '(none)'}")
        print(f"  >> {result['decision'].upper()} (confidence {float(result.get('confidence', 0)):.2f}) "
              f"— {result['reason']}")


if __name__ == "__main__":
    policies = json.loads((HERE / "return_policy_kb.json").read_text())
    claims = json.loads((HERE / "sample_claims.json").read_text())
    claims_by_id = {c["id"]: c for c in claims}

    args = sys.argv[1:]
    ids = list(claims_by_id) if args == ["--all"] else (args or DEFAULT_IDS)
    run(ids, policies, claims_by_id)
