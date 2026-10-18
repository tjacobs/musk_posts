"""Join labels to posts and write yearly category shares to data/summary.json and data/labeled_tweets.csv."""
import glob, json, os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUP = {'us_politics': 'Politics', 'government': 'Politics', 'intl_politics': 'Politics',
         'immigration_crime': 'Politics', 'free_speech': 'Rights & media', 'media': 'Rights & media',
         'culture_society': 'Rights & media', 'tesla': 'Companies', 'spacex': 'Companies',
         'x_platform': 'Companies', 'ai': 'Companies', 'other_ventures': 'Companies',
         'science_tech': 'Science & tech', 'economy': 'Economy & crypto', 'crypto': 'Economy & crypto',
         'news_events': 'News & events', 'humor': 'Humor & personal', 'personal': 'Humor & personal',
         'low_content': 'Unclassifiable'}

df = pd.read_csv(os.path.join(ROOT, 'data/tweets.csv'), dtype={'id': str})
ctx = {}
for line in open(os.path.join(ROOT, 'data/context.jsonl')):
    r = json.loads(line)
    ctx[r['id']] = r
labels = [r for f in sorted(glob.glob(os.path.join(ROOT, 'data/labels/batch_*.json'))) for r in json.load(open(f))]
lab = pd.DataFrame(labels).drop_duplicates('id')
df = df.merge(lab, on='id', how='left')
df['kind'] = df['id'].map(lambda i: 'quote' if (ctx.get(i) or {}).get('quoted_text') else 'own post')
df['group'] = df['primary'].map(GROUP)
df['secondary'] = df['secondary'].map(lambda s: s if isinstance(s, list) else [])
df[['id', 'created_at', 'year', 'kind', 'primary', 'secondary', 'group', 'text']].to_csv(
    os.path.join(ROOT, 'data/labeled_tweets.csv'), index=False)

lab_df = df[df['primary'].notna()]
years = sorted(lab_df['year'].unique())


def shares(frame, col):
    out = {}
    for y in years:
        g = frame[frame.year == y]
        known = g[g['primary'] != 'low_content']
        counts = known[col].value_counts()
        out[int(y)] = {'n': int(len(g)), 'n_classified': int(len(known)),
                       'unclassifiable_pct': round(100 * (1 - len(known) / len(g)), 1) if len(g) else None,
                       'pct': {k: round(100 * v / len(known), 2) for k, v in counts.items()} if len(known) else {}}
    return out


def touches(frame, cats):
    """Share of classified posts with any of `cats` as primary or secondary label."""
    out = {}
    for y in years:
        g = frame[(frame.year == y) & (frame['primary'] != 'low_content')]
        hit = g.apply(lambda r: r['primary'] in cats or any(s in cats for s in r['secondary']), axis=1)
        out[int(y)] = round(100 * hit.mean(), 2) if len(g) else None
    return out


politics = [k for k, v in GROUP.items() if v == 'Politics']
summary = {
    'n_total': int(len(df)), 'n_labeled': int(len(lab_df)),
    'by_group': shares(lab_df, 'group'),
    'by_category': shares(lab_df, 'primary'),
    'by_group_kind': {k: shares(lab_df[lab_df.kind == k], 'group') for k in ('own post', 'quote')},
    'touches_politics': touches(lab_df, politics),
    'overall_category': {k: round(100 * v, 2) for k, v in
                         lab_df[lab_df.primary != 'low_content']['primary'].value_counts(normalize=True).items()},
}
json.dump(summary, open(os.path.join(ROOT, 'data/summary.json'), 'w'), indent=1)
print(f"{summary['n_labeled']}/{summary['n_total']} labeled")
for y, v in summary['by_group'].items():
    top = ', '.join(f'{k} {p:.0f}%' for k, p in sorted(v['pct'].items(), key=lambda kv: -kv[1])[:4])
    print(f"{y}: n={v['n']:5d} unclass={v['unclassifiable_pct']}% | {top}")
