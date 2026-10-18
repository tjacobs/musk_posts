"""Label image-only posts with Claude Haiku, which looks at each image through the CLI's Read tool.

Usage: classify_images.py [--ids ID,ID,...] [--limit N_BATCHES] [--workers W] [--out DIR]
Reads every data/images/<id>.jpg (or just --ids). Resumable per batch of 8 images.
"""
import argparse, glob, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import classify  # noqa: E402  (reuses the topic list, schema and the clean CLI environment)

IMG_DIR = os.path.join(ROOT, 'data/images')
BATCH = 8
SYSTEM = classify.SYSTEM.replace(
    'You have no tools; answer only with the structured output.',
    'Each post here is only an image (or the preview frame of a video or GIF) with no text of his own. '
    'Use the Read tool to look at every image listed, then answer with the structured output.',
) + '\nFor an image, label what it is about: a chart or meme about gender is culture_society, a screenshot of a news story takes the topic of the story. Use low_content only if the image gives no readable topic.'
SCHEMA = json.loads(json.dumps(classify.SCHEMA))


def run_batch(k, ids, out_dir):
    listing = '\n'.join(f'[{i}] {tid}.jpg' for i, tid in enumerate(ids))
    prompt = f'Read each of these images in the current folder, then label each post by its image:\n\n{listing}'
    cmd = ['claude', '-p', '--model', 'haiku', '--tools', 'Read', '--allowedTools', 'Read', '--strict-mcp-config',
           '--no-session-persistence', '--system-prompt', SYSTEM, '--output-format', 'json',
           '--json-schema', json.dumps(SCHEMA)]
    err = ''
    for _ in range(3):
        if classify.STOP.is_set():
            return k, 0, 'skipped: usage limit reached'
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=IMG_DIR, timeout=900, env=classify.CLEAN_ENV)
        try:
            res = json.loads(p.stdout)
            if res.get('api_error_status') == 429:
                classify.STOP.set()
                return k, 0, f"usage limit: {res.get('result')}"
            labels = (res.get('structured_output') or json.loads(res['result']))['labels']
        except Exception as e:
            err = f'{e}: {p.stdout[-200:]} {p.stderr[-200:]}'
            continue
        got = {l['n']: l for l in labels if 0 <= l['n'] < len(ids)}
        if len(got) < len(ids) * 0.75:
            err = f'only {len(got)}/{len(ids)} labels'
            continue
        out = [dict(id=t, primary=got[i]['primary'], secondary=got[i]['secondary']) if i in got
               else dict(id=t, primary=None, secondary=[]) for i, t in enumerate(ids)]
        json.dump(out, open(os.path.join(out_dir, f'batch_{k:04d}.json'), 'w'))
        return k, len(got), res.get('total_cost_usd')
    return k, 0, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--out', default=os.path.join(ROOT, 'data/labels_images'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ids = a.ids.split(',') if a.ids else sorted(os.path.basename(f)[:-4] for f in glob.glob(f'{IMG_DIR}/*.jpg'))
    batches = [(k, ids[s:s + BATCH]) for k, s in enumerate(range(0, len(ids), BATCH))
               if not os.path.exists(os.path.join(a.out, f'batch_{k:04d}.json'))]
    if a.limit:
        batches = batches[:a.limit]
    print(f'{len(batches)} batches of up to {BATCH} images', flush=True)
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [pool.submit(run_batch, k, b, a.out) for k, b in batches]
        for n, f in enumerate(as_completed(futs), 1):
            k, ok, info = f.result()
            print(f'[{n}/{len(batches)}] batch {k}: {ok} labels' + (f' ({info})' if not ok else ''), flush=True)


if __name__ == '__main__':
    main()
