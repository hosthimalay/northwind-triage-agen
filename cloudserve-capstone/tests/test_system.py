import json
from pathlib import Path
import sqlite3
from cloudserve.core import CloudServeEngine, DecisionStore, KnowledgeBase, validate_answer, normalise_ticket, DATA
from cloudserve.evaluation import run_evaluation
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope='module')
def engine():
    return CloudServeEngine(model_enabled=False)


def test_a2_four_channels(engine):
    for i, channel in enumerate(['email', 'chat', 'docs_comment', 'forum']):
        out = engine.process({'ticket_id': f'T-{i}', 'channel': channel,
                              'subject': 'Rate limits', 'body': 'How do I handle API rate limiting?'})
        assert out['channel'] == channel
        assert out['route'] in ('escalate', 'auto_respond')


def test_a3_classifier_confidence(engine):
    r = engine.process({'ticket_id': 'S1', 'channel': 'email',
                        'body': 'Our deployment build fails during dependency resolution.'})
    assert r['intent'] and r['urgency']
    assert 0 <= r['intent_confidence'] <= 1
    assert 0 <= r['urgency_confidence'] <= 1
    assert len(r['alternatives']) >= 1


def test_a4_verifiable_retrieval(engine):
    matches = engine.kb.search('Rate limit API requests and quota tiers', threshold=0.0)
    assert matches and matches[0].doc_id in engine.kb.documents
    assert matches[0].text == engine.kb.documents[matches[0].doc_id]['content']


def test_a5_route_is_deterministic(engine):
    t = {'ticket_id': 'S2', 'channel': 'chat', 'body': 'How do API rate limits work?'}
    assert engine.process(t)['route'] == engine.process(t)['route']


def test_a6_citations_verified(engine):
    r = engine.process({'ticket_id': 'S3', 'channel': 'chat', 'body': 'Explain API rate limits and quota tiers'})
    assert r['route'] == 'auto_respond'
    assert r['citations']
    assert {c['doc_id'] for c in r['citations']} <= {s['doc_id'] for s in r['sources']}
    assert not validate_answer(r['answer'], r['citations'], engine.kb)
    assert 'citation_mismatch' in validate_answer(r['answer'] + '\nUnverified statement.', r['citations'], engine.kb)


def test_a7_security_guardrail_blocks(engine):
    r = engine.process({'ticket_id': 'S4', 'channel': 'chat',
                        'body': 'Our production API key has been stolen, please fix the compromise.'})
    assert r['route'] == 'escalate'
    assert 'compromise' in r['guardrails']
    assert r['answer'] is None


def test_a7_operator_pause_and_monitoring(tmp_path, engine, monkeypatch):
    from cloudserve import api

    monkeypatch.setattr(api, 'engine', lambda: engine)
    monkeypatch.setattr(api, 'AUDIT_PATH', tmp_path / 'api.sqlite3')
    pause_file = tmp_path / 'pause-auto-drafts'
    monkeypatch.setattr(api, 'PAUSE_FILE', pause_file)
    ticket = {'ticket_id': 'PAUSE', 'channel': 'chat',
              'subject': 'HTTP 429 Too Many Requests API rate limit exceeded',
              'body': 'Requests exceed rate limit, please explain quota and backoff.'}

    with TestClient(api.app) as client:
        pause_file.touch()
        blocked = client.post('/tickets', json=ticket).json()
        assert blocked['route'] == 'escalate'
        assert blocked['answer'] is None
        assert blocked['guardrails'] == ['automation_paused']
        pause_file.unlink()
        assert client.post('/tickets', json=ticket).json()['route'] == 'auto_respond'
        metrics = client.get('/metrics/')
        assert metrics.status_code == 200
        for sample in ('cloudserve_tickets_total{channel="chat",outcome="escalate"}',
                       'cloudserve_guardrail_activations_total{guardrail="automation_paused"}',
                       'cloudserve_response_seconds_bucket', 'cloudserve_confidence_bucket'):
            assert sample in metrics.text
        assert 'PAUSE' not in metrics.text

    with sqlite3.connect(api.AUDIT_PATH) as connection:
        routes = connection.execute('SELECT route FROM decisions ORDER BY rowid').fetchall()
    assert routes == [('escalate',), ('auto_respond',)]

    checks = iter([False, True])
    late_pause = engine.process(ticket, pause_auto_drafts=lambda: next(checks))
    assert late_pause['guardrails'] == ['automation_paused']
    assert late_pause['answer'] is None


def test_a7_unsupported_claim_blocked(engine):
    kb = engine.kb
    doc = next(iter(kb.documents))
    quote = kb.documents[doc]['content'].splitlines()[0]
    answer = f'We guarantee a refund tomorrow. {quote} [{doc}]'
    assert 'unsupported_commitment' in validate_answer(answer, [{'doc_id': doc, 'excerpt': quote}], kb)


def test_a8_persistent_log(tmp_path, engine):
    store = DecisionStore(tmp_path / 'events.db')
    store.save('test-run', engine.process({'ticket_id': 'X', 'channel': 'forum', 'body': 'Bad login'}))
    assert store.count('test-run') == 1
    store.close()
    assert sqlite3.connect(tmp_path / 'events.db').execute('select count(*) from decisions').fetchone()[0] == 1


def test_a9_a10_batch_and_metrics(tmp_path):
    source = tmp_path / 'unknown.json'
    tickets = [{'ticket_id': f'B-{i}', 'channel': ['email','chat','docs_comment','forum'][i%4],
                'body': 'How do I configure API rate limits and quotas?'} for i in range(8)]
    tickets[7]['body'] = ''
    tickets[:3] = [{'ticket_id': 'collision-2', 'labels': None, 'history': None},
                   {'ticket_id': 'collision', 'labels': {'expected_doc_ids': [[]]}},
                   {'ticket_id': 'collision', 'channel': 'email', 'body': '\ud800'}]
    source.write_text(json.dumps(tickets))
    metrics = run_evaluation(source, tmp_path / 'results')
    assert metrics['volume']['tickets_processed'] == 8
    assert metrics['governance']['logging_reconciled']
    assert len((tmp_path / 'results' / 'results.jsonl').read_text().splitlines()) == 8
    assert (tmp_path / 'results' / 'metrics.json').exists()
    with sqlite3.connect(tmp_path / 'results' / 'decisions.sqlite3') as connection:
        rows = connection.execute('SELECT ticket_id, record FROM decision_audit').fetchall()
    assert len(rows) == 8
    for ticket_id, record in rows:
        audit = json.loads(record)
        assert audit['ticket_id'] == ticket_id
        assert audit['decision_id'] and audit['requirement_ids']


def test_a11_malformed_and_missing_docs(engine):
    for t in [None, {'ticket_id': 'blank', 'body': ''}, {'ticket_id': 'bad','channel':'bogus', 'body': '???'}]:
        r = engine.process(t)
        assert r['route'] == 'escalate' and r['reason']


@pytest.mark.parametrize('error', [TimeoutError, ConnectionError, type('RateLimitError', (Exception,), {})])
def test_a11_provider_outage_fails_closed(engine, monkeypatch, error):
    import cloudserve.core as core
    def down(*a, **k):
        raise error('Simulated model provider failure')
    monkeypatch.setattr(core, '_openai_selected', down)
    engine.model_enabled = True
    try:
        r = engine.process({'ticket_id': 'outage', 'channel': 'chat',
                            'body': 'Explain API rate limits and quota tiers'})
        assert r['route'] == 'escalate'
        assert 'generation_failure' in r['guardrails']
        assert r['answer'] is None
    finally:
        engine.model_enabled = False


def test_secret_not_echoed(engine):
    r = engine.process({'ticket_id': 'private', 'channel': 'email',
                        'body': 'My OpenAI key is sk-abcdefghijklmnopqrstuvwxyz1234. Please help with API rate limits.'})
    assert 'sk-abcdefghijklmnopqrstuvwxyz1234' not in (r['answer'] or '')


def test_wording_invariance_for_intent(engine):
    examples = [
        'HTTP 429 Too Many Requests after exceeding API rate limit',
        'API requests are getting rate limited, need exponential backoff',
    ]
    assert all(engine.classifier.predict(t)['intent'] == 'rate_limit' for t in examples)


def test_evidence_draft_does_not_claim_llm_generated(engine):
    from cloudserve.core import _evidence_answer
    evidence = engine.kb.search('API quota and rate limits', threshold=0.0)
    answer, citations = _evidence_answer(evidence)
    assert 'AI-generated' not in answer
    assert citations


def test_provider_input_data_minimisation():
    from cloudserve.core import redact_before_provider
    text = 'Contact alice@example.org using key sk-abcdefghijklmnopqrstuvwxyz123456'
    cleaned = redact_before_provider(text)
    assert 'alice@example.org' not in cleaned
    assert 'sk-abcdefghijklmnopqrstuvwxyz123456' not in cleaned
    assert cleaned.count('[REDACTED]') == 2


def test_openai_enabled_evidence_selection_with_mock(engine, monkeypatch):
    # This verifies application integration, NOT a live provider call.
    import cloudserve.core as core
    monkeypatch.setattr(core, '_openai_selected', lambda sources,ticket: [
        (sources[0].doc_id, core.source_steps(sources[0].text)[0])])
    engine.model_enabled = True
    try:
        r = engine.process({'ticket_id':'mocked-openai', 'channel':'chat',
            'subject':'HTTP 429 Too Many Requests API rate limit exceeded',
            'body':'Requests exceed rate limit, please explain quota and backoff.'})
        assert r['route']=='auto_respond'
        assert r['generator']=='openai_evidence_selection'
        assert r['citations']
    finally:
        engine.model_enabled = False


def test_bad_model_evidence_fails_closed(engine, monkeypatch):
    import cloudserve.core as core
    monkeypatch.setattr(core, '_openai_selected', lambda sources,ticket: [
        ('DOC-DOES-NOT-EXIST','manufactured policy')])
    engine.model_enabled = True
    try:
        r = engine.process({'ticket_id':'bad-citation','channel':'chat',
            'subject':'HTTP 429 Too Many Requests API rate limit exceeded',
            'body':'Requests exceed rate limit, please explain quota and backoff.'})
        assert r['route']=='escalate'
        assert 'generation_failure' in r['guardrails']
        assert r['answer'] is None
    finally:
        engine.model_enabled = False


def test_historical_prior_never_bypasses_relevance_gate(engine):
    # A known intent must not force a matching doc for nonsense queries.
    found = engine.kb.search('zzzxqv gibberish unrelated', threshold=0.3,
                             intent='rate_limit')
    assert found == []


def test_reranker_uses_development_only(engine):
    kb = engine.kb
    assert kb.doc_priors['rate_limit']['DOC-API-001'] >= 1
    for doc in kb.search('HTTP 429 API rate limit exceeded', intent='rate_limit'):
        assert doc.ranking_score >= doc.score


def test_lambda_handler_local_adapter_with_mocked_store(monkeypatch):
    from cloudserve import aws_handler
    saved=[]
    monkeypatch.setattr(aws_handler, '_persist', lambda record: saved.append(record))
    event={'rawPath':'/tickets','requestContext':{'http':{'method':'POST'}},
      'body':json.dumps({'ticket_id':'AWS-LOCAL','channel':'chat',
        'subject':'HTTP 429 API rate limit exceeded',
        'body':'API rate limit and quota exceeded; retry with exponential backoff.'})}
    r=aws_handler.handler(event,None)
    assert r['statusCode']==200
    assert json.loads(r['body'])['ticket_id']=='AWS-LOCAL'
    assert len(saved)==1


def test_lambda_fails_closed_if_audit_write_fails(monkeypatch):
    from cloudserve import aws_handler
    def fail(_):raise OSError('simulate DynamoDB failure')
    monkeypatch.setattr(aws_handler, '_persist', fail)
    event={'rawPath':'/tickets','requestContext':{'http':{'method':'POST'}},
      'body':json.dumps({'ticket_id':'AWS-AUDIT','channel':'chat',
        'body':'API quota rate limit HTTP 429 Too Many Requests.'})}
    r=aws_handler.handler(event,None)
    assert r['statusCode']==503
    assert json.loads(r['body'])['route']=='escalate'


def test_external_prompt_redacts_customer_email_and_api_key(monkeypatch):
    # Mock the OpenAI SDK; inspect the exact prompt sent without a network call.
    import sys, types, os
    import cloudserve.core as core
    seen=[]
    doc=core.KnowledgeBase(json.loads((DATA/'documentation.json').read_text()))
    source=doc.search('API 429 rate limit quota',limit=1,threshold=0)[0]
    excerpt=core.source_steps(source.text)[0]
    class FakeCompletions:
        def create(self,**kwargs):
            seen.append(kwargs)
            content=json.dumps({'selected':[{'doc_id':source.doc_id,'quote':excerpt}]})
            return types.SimpleNamespace(choices=[types.SimpleNamespace(
                message=types.SimpleNamespace(content=content))])
    class FakeOpenAI:
        def __init__(self,**kwargs):pass
        self_chat=types.SimpleNamespace(completions=FakeCompletions())
        @property
        def chat(self):return self.self_chat
    monkeypatch.setenv('OPENAI_API_KEY','fake-only-not-real')
    core._openai_key.cache_clear()
    monkeypatch.setitem(sys.modules,'openai',types.SimpleNamespace(OpenAI=FakeOpenAI))
    try:
        selected=core._openai_selected([source], {
          'subject':'Help alice@example.com',
          'body':'API rate limit with sk-abcdefghijklmnopqrstuvwxyz123456'})
        assert selected==[(source.doc_id,excerpt)]
        payload=seen[0]['messages'][-1]['content']
        assert 'alice@example.com' not in payload
        assert 'sk-abcdefghijklmnopqrstuvwxyz123456' not in payload
    finally:
        core._openai_key.cache_clear()
