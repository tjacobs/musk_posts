"""Merge the two gist dumps into one deduplicated CSV (tweets.csv)."""
import html, json, re, sys
from datetime import datetime
import pandas as pd

FMT = '%a %b %d %H:%M:%S %z %Y'
a = json.load(open('raw-gist/elonmusk-ALL-2025-12-10.json', encoding='utf-8'))
b = json.load(open('raw-gist/elonmusk_tweets_2025-11-02.json', encoding='utf-8'))

rows = {}
for r in a:
    s = r['stats']
    rows[r['id']] = dict(id=r['id'], created_at=r['created_at'], text=r['text'],
                         likes=s['likes'], retweets=s['retweets'], replies=s['replies'],
                         quotes=s['quotes'], views=s['views'], has_media=None, n_urls=None)
for r in b:  # richer fields; fills media/url info and adds any ids missing from the Dec file
    row = rows.setdefault(r['id'], dict(id=r['id'], created_at=r['createdAt'], text=r['text'],
                          likes=r['likeCount'], retweets=r['retweetCount'], replies=r['replyCount'],
                          quotes=r['quoteCount'], views=r['viewCount']))
    row['has_media'] = bool(r['media'])
    row['n_urls'] = len(r['urls'])

df = pd.DataFrame(rows.values())
df['created_at'] = pd.to_datetime(df['created_at'], format=FMT, utc=True)
df['year'] = df['created_at'].dt.year
df['text'] = df['text'].map(html.unescape)
tco = re.compile(r'https://t\.co/\w+')
df['clean_text'] = df['text'].str.replace(tco, '', regex=True).str.strip()
df['link_only'] = df['clean_text'].eq('')
df['n_words'] = df['clean_text'].str.split().str.len().fillna(0).astype(int)
df = df.sort_values('created_at').reset_index(drop=True)
df.to_csv('data/tweets.csv', index=False)
print(len(df), 'tweets ->', 'data/tweets.csv')
print(df.groupby('year').agg(n=('id', 'size'), link_only=('link_only', 'sum'),
                             short=('n_words', lambda s: (s <= 3).sum())).to_string())
