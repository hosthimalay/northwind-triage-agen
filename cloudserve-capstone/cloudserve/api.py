"""Minimal FastAPI wrapper. Run with: uvicorn cloudserve.api:app --reload"""
from functools import lru_cache
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
from .core import CloudServeEngine, DecisionStore, ROOT
import uuid

app = FastAPI(title='CloudServe AI Support Resolution', version='0.1.0')


class TicketInput(BaseModel):
    model_config = ConfigDict(extra='allow')
    ticket_id: str
    channel: str
    subject: str = ''
    body: str = ''


@lru_cache(maxsize=1)
def engine():
    return CloudServeEngine()


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/tickets')
def evaluate_ticket(ticket: TicketInput):
    result = engine().process(ticket.model_dump())
    store = DecisionStore(ROOT / 'storage' / 'api_decisions.sqlite3')
    try:
        store.save(uuid.uuid4().hex, result)
    finally:
        store.close()
    return result
