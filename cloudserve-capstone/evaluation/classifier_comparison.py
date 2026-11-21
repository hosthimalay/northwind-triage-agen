"""Compare intent model robustness without using the 80 validation tickets.

python -m evaluation.classifier_comparison
"""
import json
from pathlib import Path
from statistics import mean
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score
from cloudserve.core import DATA, _text_of


def compare():
    dev=json.loads((DATA/'development_tickets.json').read_text(encoding='utf-8'))
    x=[_text_of(t) for t in dev]
    y=[t['labels']['intent'] for t in dev]
    group=[(t.get('body') or '').strip().casefold() for t in dev]
    results=[]
    for seed in (42,17,77,110):
        tr,te=next(GroupShuffleSplit(test_size=.22,random_state=seed).split(x, groups=group))
        row={'seed':seed,'train_size':len(tr),'holdout_size':len(te)}
        for name,analyzer,ngram in [('word', 'word',(1,2)),
                                     ('character','char_wb',(3,5))]:
            pipe=Pipeline([('tfidf',TfidfVectorizer(analyzer=analyzer,
                ngram_range=ngram,sublinear_tf=True,strip_accents='unicode')),
                ('model',LogisticRegression(max_iter=700,class_weight='balanced'))])
            pipe.fit([x[i] for i in tr],[y[i] for i in tr])
            row[name+'_accuracy']=round(accuracy_score([y[i] for i in te],
                pipe.predict([x[i] for i in te])),4)
        results.append(row)
    return {'evaluation':'grouped development holdout; not final validation',
      'per_split':results,
      'mean_word_accuracy':round(mean(r['word_accuracy'] for r in results),4),
      'mean_character_accuracy':round(mean(r['character_accuracy'] for r in results),4)}


if __name__=='__main__':
    print(json.dumps(compare(),indent=2))
