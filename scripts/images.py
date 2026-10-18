"""Download the first image (photo, or video/GIF preview frame) of each unclassified post in a year.

Usage: images.py YEAR. Saves data/images/<id>.jpg and data/images/index.json. Resumable.
"""
import json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests

YEAR = int(sys.argv[1])
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data/images')
os.makedirs(OUT, exist_ok=True)

ctx = {}
for line in open(os.path.join(ROOT, 'data/context.jsonl')):
    r = json.loads(line)
    ctx[r['id']] = r
lab = pd.read_csv(os.path.join(ROOT, 'data/labeled_tweets.csv'), dtype={'id': str})
ids = [i for i in lab[(lab.year == YEAR) & (lab.primary == 'low_content')].id if (ctx.get(i) or {}).get('media')]
print(len(ids), 'posts with media', flush=True)

local = threading.local()
def sess():
    if not hasattr(local, 's'):
        local.s = requests.Session(); local.s.headers['User-Agent'] = 'Mozilla/5.0'
    return local.s

def get(tid):
    path = os.path.join(OUT, f'{tid}.jpg')
    if os.path.exists(path):
        return tid, 'cached', None
    try:
        d = sess().get('https://cdn.syndication.twimg.com/tweet-result', params={'id': tid, 'token': 'x'}, timeout=20).json()
        md = (d.get('mediaDetails') or [None])[0]
        if not md:
            return tid, 'no-media', None
        img = sess().get(md['media_url_https'], params={'name': 'medium'}, timeout=30)
        if img.status_code != 200 or not img.content:
            return tid, f'img-{img.status_code}', None
        open(path, 'wb').write(img.content)
        time.sleep(0.2)
        return tid, 'ok', md.get('type')
    except Exception as e:
        return tid, f'error: {e}', None

res = {}
with ThreadPoolExecutor(4) as pool:
    for n, (tid, status, typ) in enumerate(pool.map(get, ids), 1):
        res[tid] = {'status': status, 'type': typ}
        if n % 100 == 0:
            print(f'{n}/{len(ids)}', flush=True)
json.dump(res, open(os.path.join(OUT, f'index_{YEAR}.json'), 'w'))
import collections
print(dict(collections.Counter(v['status'] for v in res.values())), flush=True)
