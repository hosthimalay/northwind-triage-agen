import json
from pathlib import Path
import sqlite3
from cloudserve.core import CloudServeEngine, DecisionStore, KnowledgeBase, validate_answer, normalise_ticket, DATA
from cloudserve.evaluation import run_evaluation
import pytest


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
    if r['route'] == 'auto_respond':
        assert r['citations']
        assert not validate_answer(r['answer'], r['citations'], engine.kb)


def test_a7_security_guardrail_blocks(engine):
    r = engine.process({'ticket_id': 'S4', 'channel': 'chat',
                        'body': 'Our production API key has been stolen, please fix the compromise.'})
    assert r['route'] == 'escalate'
    assert 'compromise' in r['guardrails']
    assert r['answer'] is None


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
    source.write_text(json.dumps(tickets))
    metrics = run_evaluation(source, tmp_path / 'results')
    assert metrics['volume']['tickets_processed'] == 8
    assert metrics['governance']['logging_reconciled']
    assert len((tmp_path / 'results' / 'results.jsonl').read_text().splitlines()) == 8
    assert (tmp_path / 'results' / 'metrics.json').exists()


def test_a11_malformed_and_missing_docs(engine):
    for t in [None, {'ticket_id': 'blank', 'body': ''}, {'ticket_id': 'bad','channel':'bogus', 'body': '???'}]:
        r = engine.process(t)
        assert r['route'] == 'escalate' and r['reason']


def test_a11_provider_outage_fails_closed(engine, monkeypatch):
    import cloudserve.core as core
    def down(*a, **k):
        raise TimeoutError('Simulated model provider outage')
    monkeypatch.setattr(core, '_openai_selected', down)
    engine.model_enabled = True
    try:
        r = engine.process({'ticket_id': 'outage', 'channel': 'chat',
                            'body': 'Explain API rate limits and quota tiers'})
        if r['intent_confidence'] >= engine.confidence_threshold and r['sources']:
            assert r['route'] == 'escalate'
            assert 'generation_failure' in r['guardrails']
    finally:
        engine.model_enabled = False


def test_secret_not_echoed(engine):
    r = engine.process({'ticket_id': 'private', 'channel': 'email',
                        'body': 'My OpenAI key is sk-abcdefghijklmnopqrstuvwxyz1234. Please help with API rate limits.'})
    assert 'sk-abcdefghijklmnopqrstuvwxyz1234' not in (r['answer'] or '')
