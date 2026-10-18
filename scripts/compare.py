"""Compare model labels in a labels dir against data/validation_labels.json."""
import glob, json, sys, collections
labdir = sys.argv[1] if len(sys.argv) > 1 else 'data/labels'
hand = json.load(open('data/validation_labels.json'))
model = {}
for f in glob.glob(f'{labdir}/batch_*.json'):
    for r in json.load(open(f)):
        model[r['id']] = r
ids = [i for i in hand if i in model]
prim = sum(model[i]['primary'] == hand[i] for i in ids)
loose = sum(model[i]['primary'] == hand[i] or hand[i] in model[i]['secondary'] for i in ids)
ROLL = {'us_politics': 'Politics', 'government': 'Politics', 'intl_politics': 'Politics', 'immigration_crime': 'Politics',
        'free_speech': 'Rights & media', 'media': 'Rights & media', 'culture_society': 'Rights & media',
        'tesla': 'Companies', 'spacex': 'Companies', 'x_platform': 'Companies', 'ai': 'Companies', 'other_ventures': 'Companies',
        'science_tech': 'Science & tech', 'economy': 'Economy', 'crypto': 'Economy', 'news_events': 'News',
        'humor': 'Personal & humor', 'personal': 'Personal & humor', 'low_content': 'Unclassifiable'}
roll = sum(ROLL[model[i]['primary']] == ROLL[hand[i]] for i in ids)
n = len(ids)
print(f'{n} compared | exact primary {prim/n:.0%} | primary-or-secondary {loose/n:.0%} | roll-up group {roll/n:.0%}')
conf = collections.Counter((hand[i], model[i]['primary']) for i in ids if model[i]['primary'] != hand[i])
print('most common disagreements (mine -> model):')
for (h, m), c in conf.most_common(15):
    print(f'  {c:2d}  {h:18s} -> {m}')
