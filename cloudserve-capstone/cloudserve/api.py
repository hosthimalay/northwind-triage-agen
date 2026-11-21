"""Minimal FastAPI wrapper. Run with: uvicorn cloudserve.api:app --reload"""
import uuid
from functools import lru_cache
from typing import Any

from fastapi import FastAPI
from prometheus_client import CollectorRegistry, Counter, Histogram, make_asgi_app
from pydantic import BaseModel, ConfigDict

from .core import CloudServeEngine, DecisionStore, ROOT

app = FastAPI(title='CloudServe AI Support Resolution', version='0.2.0')
registry = CollectorRegistry()
tickets = Counter('cloudserve_tickets', 'Persisted ticket decisions', ('channel', 'outcome'), registry=registry)
latency = Histogram('cloudserve_response_seconds', 'Ticket processing latency in seconds', registry=registry,
                    buckets=(.001, .0025, .005, .01, .025, .05, .1, .25, .5, 1, 2, 3, 5, 10, 30))
guards = Counter('cloudserve_guardrail_activations', 'Guardrail findings', ('guardrail',), registry=registry)
confidence = Histogram('cloudserve_confidence', 'Classification confidence', ('prediction',), registry=registry,
                       buckets=(0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1))
app.mount('/metrics', make_asgi_app(registry=registry))

AUDIT_PATH = ROOT / 'storage' / 'api_decisions.sqlite3'
PAUSE_FILE = ROOT / 'storage' / 'pause-auto-drafts'


class TicketInput(BaseModel):
    model_config = ConfigDict(extra='allow', json_schema_extra={'example': {
        'ticket_id': 'DEMO-003', 'channel': 'chat',
        'subject': 'HTTP 429 Too Many Requests API rate limit exceeded',
        'body': 'Requests exceed rate limit, please explain quota and backoff.'
    }})
    ticket_id: str = ''
    channel: str = ''
    subject: str = ''
    body: str = ''


@lru_cache(maxsize=1)
def engine():
    return CloudServeEngine()


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/tickets', response_model=dict[str, Any])
def evaluate_ticket(ticket: TicketInput):
    result = engine().process(ticket.model_dump(), pause_auto_drafts=PAUSE_FILE.is_file)
    store = DecisionStore(AUDIT_PATH)
    try:
        store.save(uuid.uuid4().hex, result)
    finally:
        store.close()
    tickets.labels(result['channel'], result['route']).inc()
    latency.observe(result['latency_ms'] / 1000)
    confidence.labels('intent').observe(result['intent_confidence'])
    confidence.labels('urgency').observe(result['urgency_confidence'])
    for guard in result['guardrails']:
        guards.labels(guard).inc()
    return result
