"""Minimal FastAPI wrapper. Run with: uvicorn cloudserve.api:app --reload"""
from functools import lru_cache
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
from typing import Any
from .core import CloudServeEngine, DecisionStore, ROOT
import uuid

app = FastAPI(title='CloudServe AI Support Resolution', version='0.2.0')


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
    result = engine().process(ticket.model_dump())
    store = DecisionStore(ROOT / 'storage' / 'api_decisions.sqlite3')
    try:
        store.save(uuid.uuid4().hex, result)
    finally:
        store.close()
    return result
