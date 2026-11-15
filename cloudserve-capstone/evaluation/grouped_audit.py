"""Check duplicate leakage and out-of-body-group generalisation on development only."""
import json
from pathlib import Path
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score
from cloudserve.core import TicketClassifier, DATA, _text_of


def main():
    dev = json.loads((DATA / 'development_tickets.json').read_text())
    val = json.loads((DATA / 'validation_tickets.json').read_text())
    body = lambda t: (t.get('body') or '').casefold().strip()
    train_bodies = {body(t) for t in dev}
    same_body = sum(body(t) in train_bodies for t in val)
    exact = {(t.get('subject','').casefold().strip(), body(t)) for t in dev}
    same_exact = sum((t.get('subject','').casefold().strip(), body(t)) in exact for t in val)
    train, test = next(GroupShuffleSplit(test_size=.22, random_state=42).split(dev, groups=[body(t) for t in dev]))
    clf = TicketClassifier([dev[i] for i in train])
    y = [clf.predict(_text_of(dev[i])) for i in test]
    metrics = {'development_records':len(dev), 'validation_records':len(val),
        'validation_body_overlap':same_body, 'validation_subject_body_overlap':same_exact,
        'grouped_holdout_size':len(test),
        'grouped_intent_accuracy':accuracy_score([dev[i]['labels']['intent'] for i in test],[z['intent'] for z in y]),
        'grouped_urgency_accuracy':accuracy_score([dev[i]['labels']['urgency'] for i in test],[z['urgency'] for z in y])}
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__': main()
