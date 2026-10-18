"""Fetch quoted-tweet / reply / link context for each post from X's public embed endpoint.

Resumable: appends one JSON line per tweet to data/context.jsonl and skips ids already there.
Short and link-only posts go first since they are unclassifiable without context.
"""
import json, os, threading, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests

OUT = 'data/context.jsonl'
URL = 'https://cdn.syndication.twimg.com/tweet-result'
DELAY = 0.5  # per worker
WORKERS = 4

df = pd.read_csv('data/tweets.csv', dtype={'id': str})
df['priority'] = (df['n_words'] > 8).astype(int)
ids = df.sort_values(['priority', 'created_at'], ascending=[True, False])['id'].tolist()

done = set()
if os.path.exists(OUT):
    with open(OUT) as f:
        done = {json.loads(line)['id'] for line in f}
todo = [i for i in ids if i not in done]
print(f'{len(done)} cached, {len(todo)} to fetch', flush=True)

local = threading.local()
lock = threading.Lock()


def fetch(tid):
    if not hasattr(local, 's'):
        local.s = requests.Session()
        local.s.headers['User-Agent'] = 'Mozilla/5.0'
    r = None
    for attempt in range(5):
        try:
            r = local.s.get(URL, params={'id': tid, 'token': 'x'}, timeout=20)
        except requests.RequestException:
            time.sleep(5 * (attempt + 1)); continue
        if r.status_code == 429:
            time.sleep(60 * (attempt + 1)); continue
        break
    rec = {'id': tid, 'status': r.status_code if r is not None else 0}
    if r is not None and r.status_code == 200 and r.text.strip():
        d = r.json()
        q = d.get('quoted_tweet') or {}
        card = (d.get('card') or {}).get('binding_values') or {}
        rec.update(
            quoted_user=(q.get('user') or {}).get('screen_name'),
            quoted_text=q.get('text'),
            reply_to_user=d.get('in_reply_to_screen_name'),
            card_title=(card.get('title') or {}).get('string_value'),
            urls=[u.get('expanded_url') for u in (d.get('entities') or {}).get('urls', [])],
            media=[m.get('type') for m in d.get('mediaDetails', [])],
        )
    time.sleep(DELAY)
    return rec


with open(OUT, 'a') as out, ThreadPoolExecutor(WORKERS) as pool:
    for n, rec in enumerate(pool.map(fetch, todo), 1):
        with lock:
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            out.flush()
        if n % 250 == 0:
            print(f'{n}/{len(todo)} fetched', flush=True)
print('done', flush=True)
