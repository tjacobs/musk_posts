"""Classify posts with Claude Haiku via the Claude Code CLI in headless mode.

Usage: classify.py [--limit N_BATCHES] [--workers W] [--ids-file FILE] [--out DIR]
Resumable: each batch of 100 posts is written to <out>/batch_NNNN.json; existing batches are skipped.
"""
import argparse, json, os, re, subprocess, sys, tempfile, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATCH = 100
# Launched from inside the Claude desktop app, the inherited CLAUDE_*/ANTHROPIC_* variables point the
# CLI at the app's own auth; a minimal env makes it use the user's own `claude auth login` session.
STOP = threading.Event()  # set when the plan's usage limit is hit; remaining batches are skipped
CLEAN_ENV = {k: os.environ[k] for k in ('HOME', 'USER', 'PATH', 'LANG') if k in os.environ}
CATS = ['us_politics', 'government', 'intl_politics', 'immigration_crime', 'free_speech', 'media',
        'culture_society', 'tesla', 'spacex', 'x_platform', 'ai', 'other_ventures', 'science_tech',
        'economy', 'crypto', 'news_events', 'humor', 'personal', 'low_content']

SCHEMA = {
    'type': 'object',
    'properties': {'labels': {'type': 'array', 'items': {
        'type': 'object',
        'properties': {'n': {'type': 'integer'},
                       'primary': {'type': 'string', 'enum': CATS},
                       'secondary': {'type': 'array', 'items': {'type': 'string', 'enum': CATS}, 'maxItems': 2}},
        'required': ['n', 'primary', 'secondary']}}},
    'required': ['labels'],
}

table = open(os.path.join(ROOT, 'categories.md')).read()
SYSTEM = f"""You label posts by Elon Musk on X by topic. You have no tools; answer only with the structured output.

{table}

Each input post is numbered [n] and may include the tweet it QUOTES and a LINK title. Musk's own words are often a short reaction ("Yes", "Wow", "!!", "Exactly", "Concerning"); in that case the topic comes from the quoted tweet or link. Use low_content only when neither the post nor its context indicates a topic.
Return exactly one label object per input post, using its number n."""


def load():
    df = pd.read_csv(os.path.join(ROOT, 'data/tweets.csv'), dtype={'id': str})
    ctx = {}
    path = os.path.join(ROOT, 'data/context.jsonl')
    if os.path.exists(path):
        for line in open(path):
            r = json.loads(line)
            ctx[r['id']] = r
    return df, ctx


def clip(s, n):
    s = re.sub(r'https://t\.co/\w+', '', s or '').replace('\n', ' ').strip()
    return s if len(s) <= n else s[:n] + '…'


def render(i, row, ctx):
    c = ctx.get(row.id, {})
    text = clip(row.text, 500) or '(no text — media or link only)'
    lines = [f'[{i}] ({row.year}) {text}']
    if c.get('quoted_text'):
        lines.append(f'    QUOTES @{c.get("quoted_user")}: {clip(c["quoted_text"], 400)}')
    if c.get('card_title'):
        lines.append(f'    LINK: {clip(c["card_title"], 150)}')
    elif not c.get('quoted_text') and c.get('urls'):
        lines.append(f'    LINK: {", ".join(u for u in c["urls"][:2] if u)}')
    if not c.get('quoted_text') and c.get('media') and row.n_words <= 3:
        lines.append(f'    (has {"/".join(sorted(set(c["media"])))} attached, not visible)')
    return '\n'.join(lines)


def run_batch(k, rows, ctx, out_dir, workdir):
    prompt = 'Label these posts:\n\n' + '\n'.join(render(i, r, ctx) for i, r in enumerate(rows))
    cmd = ['claude', '-p', '--model', 'haiku', '--tools', '', '--strict-mcp-config',
           '--no-session-persistence', '--system-prompt', SYSTEM,
           '--output-format', 'json', '--json-schema', json.dumps(SCHEMA)]
    for attempt in range(3):
        if STOP.is_set():
            return k, 0, 'skipped: usage limit reached'
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=workdir, timeout=600, env=CLEAN_ENV)
        try:
            res = json.loads(p.stdout)
            if res.get('api_error_status') == 429:
                STOP.set()
                return k, 0, f"usage limit: {res.get('result')}"
            labels = (res.get('structured_output') or json.loads(res['result']))['labels']
        except Exception as e:
            err = f'{e}: {p.stdout[-300:]} {p.stderr[-300:]}'
            continue
        got = {l['n']: l for l in labels if 0 <= l['n'] < len(rows)}
        if len(got) < len(rows) * 0.95:
            err = f'only {len(got)}/{len(rows)} labels'
            continue
        out = [dict(id=r.id, primary=got[i]['primary'], secondary=got[i]['secondary']) if i in got
               else dict(id=r.id, primary=None, secondary=[]) for i, r in enumerate(rows)]
        json.dump(out, open(os.path.join(out_dir, f'batch_{k:04d}.json'), 'w'))
        return k, len(got), res.get('total_cost_usd')
    return k, 0, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--ids-file')
    ap.add_argument('--out', default=os.path.join(ROOT, 'data/labels'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    df, ctx = load()
    if a.ids_file:
        keep = set(open(a.ids_file).read().split())
        df = df[df.id.isin(keep)]
    rows = list(df.itertuples())
    batches = [(k, rows[s:s + BATCH]) for k, s in enumerate(range(0, len(rows), BATCH))
               if not os.path.exists(os.path.join(a.out, f'batch_{k:04d}.json'))]
    if a.limit:
        batches = batches[:a.limit]
    print(f'{len(batches)} batches to run', flush=True)
    workdir = tempfile.mkdtemp(prefix='musk-classify-')  # empty cwd: no project files or CLAUDE.md
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(run_batch, k, b, ctx, a.out, workdir) for k, b in batches]
        for n, f in enumerate(as_completed(futs), 1):
            k, ok, info = f.result()
            print(f'[{n}/{len(batches)}] batch {k}: {ok} labels' + (f' ({info})' if not ok else ''), flush=True)


if __name__ == '__main__':
    main()
