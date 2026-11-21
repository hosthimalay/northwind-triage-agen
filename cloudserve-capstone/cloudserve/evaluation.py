"""Unattended evaluation harness; operates on any assessment JSON list schema."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import uuid

from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from .core import CloudServeEngine, DecisionStore, DATA


def pct(n, d):
    return round(n / d, 4) if d else None


def _latency(values, q):
    if not values:
        return None
    a = sorted(values)
    return round(a[min(len(a)-1, int((len(a)-1)*q))], 3)


def _metadata(ticket, key):
    value = ticket.get(key) if isinstance(ticket, dict) else None
    return value if isinstance(value, dict) else {}


def _expected_docs(ticket):
    values = _metadata(ticket, 'labels').get('expected_doc_ids')
    return {value for value in values if isinstance(value, str)} if isinstance(values, list) else set()


def _classification_metrics(tickets, results, field):
    pairs = [(label, r[field], r[field + '_confidence']) for t, r in zip(tickets, results)
             if isinstance(label := _metadata(t, 'labels').get(field), str)]
    if not pairs:
        return {'available': False, 'reason': 'No reference labels in input'}
    y_true, y_pred, _ = zip(*pairs)
    labels = sorted(set(y_true) | set(y_pred))
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0)
    bands = defaultdict(list)
    for actual, predicted, score in pairs:
        bands[min(4, int(score * 5))].append((score, actual == predicted))
    calibration = []
    for band, items in sorted(bands.items()):
        stated = statistics.mean(score for score, _ in items)
        observed = statistics.mean(correct for _, correct in items)
        calibration.append({'lower': band / 5, 'upper': (band + 1) / 5, 'n': len(items),
                            'confidence': round(stated, 4), 'accuracy': round(observed, 4),
                            'absolute_gap': round(abs(stated - observed), 4)})
    return {'available': True, 'macro_precision': round(float(precision.mean()), 4),
            'macro_recall': round(float(recall.mean()), 4),
            'confusion_matrix': {'labels': labels, 'counts': confusion_matrix(y_true, y_pred, labels=labels).tolist()},
            'calibration': calibration,
            'per_class': {label: {'precision': round(float(p), 4), 'recall': round(float(r), 4),
                                  'f1': round(float(f), 4), 'support': int(s)}
                          for label, p, r, f, s in zip(labels, precision, recall, f1, support)}}


def _segment_stats(tickets, outputs, field):
    groups = defaultdict(lambda: {'total': 0, 'auto': 0, 'unsafe_auto': 0, 'citation_ok': 0, 'citation_total': 0})
    for raw, r in zip(tickets, outputs):
        g = groups[str(raw.get(field) or 'unknown') if isinstance(raw, dict) else 'unknown']
        g['total'] += 1
        if r['route'] == 'auto_respond':
            g['auto'] += 1
        if _metadata(raw, 'labels').get('must_not_auto_respond') is True and r['route'] == 'auto_respond':
            g['unsafe_auto'] += 1
        expected = _expected_docs(raw)
        if expected:
            g['citation_total'] += len(r['citations'])
            g['citation_ok'] += sum(c['doc_id'] in expected for c in r['citations'])
    return {k: {**v, 'auto_rate': pct(v['auto'], v['total']),
                    'citation_accuracy': pct(v['citation_ok'], v['citation_total'])}
            for k, v in sorted(groups.items())}


def build_metrics(tickets, outputs, decisions_logged, run_id):
    total = len(outputs)
    auto = sum(r['route'] == 'auto_respond' for r in outputs)
    blocked = sum(bool(r['guardrails']) for r in outputs)
    latency = [r['latency_ms'] for r in outputs]
    historical = [_metadata(t, 'history').get('resolution_time_minutes') for t in tickets]
    historical = [x for x in historical if isinstance(x, (int, float))]
    historical_fcr = [value for t in tickets
                      if isinstance(value := _metadata(t, 'history').get('first_contact_resolution'), bool)]
    doc_eligible = [(expected, r) for t, r in zip(tickets, outputs) if (expected := _expected_docs(t))]
    correct_retrieval = sum(bool(expected &
                             {s['doc_id'] for s in r['sources']}) for expected, r in doc_eligible)
    cite_eligible = [(expected, r) for expected, r in doc_eligible if r['citations']]
    cite_correct = sum(c['doc_id'] in expected for expected, r in cite_eligible for c in r['citations'])
    citation_count = sum(len(r['citations']) for _, r in cite_eligible)
    hard_prohibited = [(t, r) for t, r in zip(tickets, outputs)
                       if _metadata(t, 'labels').get('must_not_auto_respond') is True]
    guard_counts = Counter(g for r in outputs for g in r['guardrails'])
    response_mean = round(statistics.mean(latency), 3) if latency else None
    return {
        'run_id': run_id,
        'volume': {'tickets_processed': total, 'answered_automatically': auto,
                   'escalated': total-auto, 'blocked_by_guardrails': blocked},
        'business': {'first_contact_resolution_proxy': pct(auto, total),
                     'first_contact_resolution_note': ('Proxy only: automated response is NOT verified issue resolution. '
                         'Actual FCR requires post-response customer outcomes; this is an upper bound.'),
                     'historical_first_contact_resolution': pct(sum(historical_fcr), len(historical_fcr)),
                     'mean_response_time_ms': response_mean,
                     'median_response_time_ms': _latency(latency, .5),
                     'response_time_note': 'Processing latency proxy, not measured end-to-end customer first response.',
                     'historical_mean_resolution_minutes': round(statistics.mean(historical), 2) if historical else None,
                     'escalation_rate': pct(total-auto, total)},
        'technical': {'intent_classification': _classification_metrics(tickets, outputs, 'intent'),
                      'urgency_classification': _classification_metrics(tickets, outputs, 'urgency'),
                      'retrieval_hit_rate': pct(correct_retrieval, len(doc_eligible)),
                      'retrieval_labeled_tickets': len(doc_eligible),
                      'citation_accuracy': pct(cite_correct, citation_count),
                      'citation_metric_note': 'Per-citation reference document match; human review is needed for ticket-level relevance and completeness.',
                      'citations_matching_reference': cite_correct,
                      'citations_evaluated': citation_count,
                      'citation_eligible_answered_tickets': len(cite_eligible),
                      'latency_median_ms': _latency(latency, .5),
                      'latency_p95_ms': _latency(latency, .95)},
        'governance': {'decisions_logged': decisions_logged,
                       'logging_reconciled': decisions_logged == total,
                       'guardrail_activations_by_type': dict(guard_counts),
                       'private_data_detections': sum('private_data:' in g for r in outputs for g in r['guardrails']),
                       'unsafe_automatic_responses': sum(r['route']=='auto_respond' for t, r in hard_prohibited),
                       'unsafe_labeled_tickets': len(hard_prohibited),
                       'fairness_slices': {f: _segment_stats(tickets, outputs, f)
                          for f in ['customer_tier', 'customer_region', 'language_fluency']}},
        'limitations': ['Evaluation labels are used for metrics only, never for ticket routing.',
                        'Automated-response rate is not actual first-contact resolution.',
                        'Confidence scores are logistic-regression probabilities; calibration requires further study.',
                        'One optional OpenAI call per answer when USE_OPENAI=1; default demonstration uses extractive fallback.']
    }


def run_evaluation(input_path, output_path, *, use_openai=False,
                   development_path=DATA / 'development_tickets.json',
                   documentation_path=DATA / 'documentation.json'):
    output = Path(output_path); output.mkdir(parents=True, exist_ok=True)
    tickets = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if not isinstance(tickets, list):
        raise ValueError('Input must be a JSON list of tickets')
    run_id = uuid.uuid4().hex
    engine = CloudServeEngine(development_path, documentation_path, model_enabled=use_openai)
    store = DecisionStore(output / 'decisions.sqlite3')
    results = []
    seen = set()
    with (output / 'results.jsonl').open('w', encoding='utf-8') as fh:
        for i, ticket in enumerate(tickets):
            result = engine.process(ticket, i)
            # Generate deterministic unique IDs for duplicate or missing IDs; never discard a ticket.
            ticket_id = result['ticket_id']
            while result['ticket_id'] in seen:
                result['ticket_id'] += f'-{i}'
            if result['ticket_id'] != ticket_id:
                result['original_ticket_id'] = ticket_id
                result['audit']['ticket_id'] = result['ticket_id']
            seen.add(result['ticket_id'])
            store.save(run_id, result)
            results.append(result)
            fh.write(json.dumps(result, ensure_ascii=False) + '\n')
    metrics = build_metrics(tickets, results, store.count(run_id), run_id)
    store.close()
    (output / 'metrics.json').write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8')
    return metrics


def main():
    p = argparse.ArgumentParser(description='CloudServe FDE unattended evaluation')
    p.add_argument('--input', required=True, help='Any JSON ticket file in the assessment schema')
    p.add_argument('--output', required=True, help='Output directory for results, SQLite log and metrics')
    p.add_argument('--use-openai', action='store_true', help='Enable optional OpenAI evidence-selection calls')
    args = p.parse_args()
    result = run_evaluation(args.input, args.output, use_openai=args.use_openai)
    print(json.dumps({'processed': result['volume']['tickets_processed'],
                      'auto': result['volume']['answered_automatically'],
                      'escalated': result['volume']['escalated'],
                      'logged': result['governance']['decisions_logged'],
                      'metrics': str(Path(args.output) / 'metrics.json')}, indent=2))


if __name__ == '__main__':
    main()
