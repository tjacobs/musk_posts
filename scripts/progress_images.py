"""Live progress view for classify_images.py. Press Ctrl+C to stop watching (the labeling keeps running)."""
import glob, json, os, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOTAL_BATCHES, TOTAL_IMAGES = 99, 786

while True:
    files = sorted(glob.glob(os.path.join(ROOT, 'data/labels_images/batch_*.json')), key=os.path.getmtime)
    rows = [r for f in files for r in json.load(open(f))]
    done = len(files)
    topic = sum(1 for r in rows if r['primary'] not in (None, 'low_content'))
    running = subprocess.run(['pgrep', '-f', 'scripts/classify_images.py'], capture_output=True).returncode == 0
    pct = 100 * done / TOTAL_BATCHES
    bar = '#' * int(pct / 2.5) + '-' * (40 - int(pct / 2.5))
    lines = ['\033[2J\033[H', 'Image labeling, 2025 posts that are only an image or video', '',
             f'[{bar}] {pct:.0f}%',
             f'batches: {done}/{TOTAL_BATCHES}   images labeled: {len(rows)}/{TOTAL_IMAGES}']
    if rows:
        lines.append(f'got a topic: {topic}/{len(rows)} ({100 * topic / len(rows):.0f}%)   still unclassified: {len(rows) - topic}')
    if len(files) >= 6 and done < TOTAL_BATCHES:
        t = [os.path.getmtime(f) for f in files]
        k = min(20, len(t) - 1)
        per = (t[-1] - t[-1 - k]) / k
        eta = (TOTAL_BATCHES - done) * per
        lines.append(f'speed: {60 / per:.1f} batches/min   ETA: ~{eta / 60:.0f} min (about {time.strftime("%I:%M %p", time.localtime(time.time() + eta))})')
    lines.append('')
    lines.append('status: ' + ('running' if running else ('finished' if done >= TOTAL_BATCHES else 'stopped before finishing')))
    print('\n'.join(lines), flush=True)
    if not running:
        break
    time.sleep(10)
