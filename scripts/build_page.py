"""Build index.html from data/summary.json, the validation labels and the page template."""
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from aggregate import GROUP  # noqa: E402  (re-runs aggregation, so summary.json is fresh)

summary = json.load(open(os.path.join(ROOT, 'data/summary.json')))

hand = json.load(open(os.path.join(ROOT, 'data/validation_labels.json')))
model = {r['id']: r for f in glob.glob(os.path.join(ROOT, 'data/labels/batch_*.json')) for r in json.load(open(f))}
ids = [i for i in hand if i in model and model[i]['primary']]
summary['validation'] = {
    'n': len(ids),
    'exact': round(100 * sum(model[i]['primary'] == hand[i] for i in ids) / len(ids), 1),
    'group': round(100 * sum(GROUP[model[i]['primary']] == GROUP[hand[i]] for i in ids) / len(ids), 1),
}

# 2010 has a single post: fold it into 2011 for every per-year table.
def fold(table):
    if '2010' not in table or '2011' not in table:
        return table
    a, b = table.pop('2010'), table['2011']
    if isinstance(a, dict):
        n = a['n_classified'] + b['n_classified']
        tot = a['n'] + b['n']
        pct = {k: round((a['pct'].get(k, 0) * a['n_classified'] + b['pct'].get(k, 0) * b['n_classified']) / n, 2)
               for k in set(a['pct']) | set(b['pct'])} if n else {}
        table['2011'] = {'n': tot, 'n_classified': n, 'pct': pct,
                         'unclassifiable_pct': round(100 * (1 - n / tot), 1) if tot else None}
    else:
        table['2011'] = b
    return table

for key in ('by_group', 'by_category', 'touches_politics'):
    summary[key] = fold(summary[key])
for k in summary['by_group_kind']:
    summary['by_group_kind'][k] = fold(summary['by_group_kind'][k])

# Example post for every bar section: the most-liked post in that year and topic group.
import pandas as pd  # noqa: E402
lab = pd.read_csv(os.path.join(ROOT, 'data/labeled_tweets.csv'), dtype={'id': str})
tw = pd.read_csv(os.path.join(ROOT, 'data/tweets.csv'), dtype={'id': str})[['id', 'likes', 'clean_text', 'n_words']]
m = lab.merge(tw, on='id')
m['likes'] = m['likes'].fillna(0)
examples = {}
for (year, grp), g in m[m.year >= 2012].groupby(['year', 'group']):
    if grp != 'Unclassifiable':
        g = g[g.n_words >= 5]  # skip bare reactions; the topic should be visible in the text
    if g.empty:
        continue
    r = g.sort_values('likes', ascending=False).iloc[0]
    text = (r.clean_text if isinstance(r.clean_text, str) else '').strip()
    examples.setdefault(str(year), {})[grp] = dict(id=r.id, text=text[:320] + ('…' if len(text) > 320 else ''),
                                                   likes=int(r.likes), topic=r.primary)
summary['examples'] = examples

tpl = open(os.path.join(ROOT, 'scripts/page_template.html')).read()
html = tpl.replace('/*__DATA__*/null', json.dumps(summary).replace('</', '<\\/'))
open(os.path.join(ROOT, 'index.html'), 'w').write(html)
print('wrote index.html', f"(validation: {summary['validation']})")
