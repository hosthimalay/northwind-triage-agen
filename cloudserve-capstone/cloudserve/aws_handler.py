"""AWS Lambda + HTTP API adapter with DynamoDB decision audit logging."""
from datetime import datetime, timezone
import json
import os
import uuid
from functools import lru_cache
from .core import CloudServeEngine


@lru_cache(maxsize=1)
def _engine():
    return CloudServeEngine()


def _persist(record):
    import boto3
    table = boto3.resource('dynamodb').Table(os.environ['AUDIT_TABLE'])
    table.put_item(Item={
        'decision_id': str(uuid.uuid4()), 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'ticket_id': record['ticket_id'], 'channel': record['channel'],
        'intent': record['intent'], 'intent_confidence': str(record['intent_confidence']),
        'urgency': record['urgency'], 'urgency_confidence': str(record['urgency_confidence']),
        'alternatives_json': json.dumps(record['alternatives']),
        'route': record['route'], 'reason': record['reason'],
        'sources_json': json.dumps(record['sources']),
        'citations_json': json.dumps(record['citations']),
        'guards_json': json.dumps(record['guardrails']),
        'generator': record['generator'], 'latency_ms': str(record['latency_ms']),
        'input_sha256': record['input_sha256'],
    })


def handler(event, context):
    path = event.get('rawPath', '/')
    method = (event.get('requestContext', {}).get('http', {}).get('method')
              or event.get('httpMethod') or 'GET').upper()
    headers = {'content-type': 'application/json'}
    if path == '/health' and method == 'GET':
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'status': 'ok'})}
    if path != '/tickets' or method != 'POST':
        return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Not found'})}
    try:
        ticket = json.loads(event.get('body') or '{}')
        result = _engine().process(ticket)
        # Fail-closed: do not authorise an automated answer if audit persistence fails.
        try:
            _persist(result)
        except Exception:
            return {'statusCode': 503, 'headers': headers,
                    'body': json.dumps({'route': 'escalate', 'reason': 'Audit storage unavailable'})}
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(result)}
    except Exception as exc:
        return {'statusCode': 500, 'headers': headers,
                'body': json.dumps({'route': 'escalate', 'reason': 'Processing unavailable',
                                    'failure_type': type(exc).__name__})}
