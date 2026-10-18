# Musk Posts

What Elon Musk posts about, by year (2012 to 2025). Each post is labeled with one of 18 topics by Claude Haiku. The topics roll up into eight categories: Companies, Humor, Science, News, Media, Politics, Economy and Unclassified.

The finished report is `index.html`, a self-contained page with a stacked bar chart by category, a sortable grid of all 18 topics, and an example post for each bar section.

## Data

18,390 posts and quote tweets from @elonmusk, June 2010 to December 10, 2025, merged and de-duplicated from two public files in [this gist](https://gist.github.com/j4ckxyz/1518890aa6d319d23a516bf14240d2b2). The page charts 2012 onward (18,353 posts).

The archive has no replies or plain reposts, so it is a fraction of everything he posted. Outside counts put 2018 to 2021 at about 2,300 to 3,400 posts a year against 425 to 434 here.

## Method

1. Merge the two gist files into `data/tweets.csv` with `scripts/merge.py`.
2. Fetch the post that each post quotes from X with `scripts/enrich.py`, so short reactions can be read in context.
3. Send batches of 100 posts to Claude Haiku through the `claude` command-line tool with `scripts/classify.py`, which writes `data/labels/`. The topic list and tie-break rules are in `categories.md`.
4. For 2025 posts that are only an image or video, download the image (or the video's preview frame) with `scripts/images.py 2025`. Have Haiku look at each one and label it with `scripts/classify_images.py`, which writes `data/labels_images/`. Watch progress with `scripts/progress_images.py`.
5. Build `data/labeled_tweets.csv` and `data/summary.json` with `scripts/aggregate.py`. It uses an image label wherever the text-only label was unclassified and the image gave a topic.
6. Fill `scripts/page_template.html` and write `index.html` with `scripts/build_page.py`.
7. Score the labels against `data/validation_labels.json` with `scripts/compare.py`. That file holds 200 posts (150 random, 50 from before 2022) labeled on its own by Claude Opus 5.5, with no person reviewing them. Haiku's topic matched Opus's 86% of the time and its category 90% of the time. This compares two Claude models; it is not accuracy against a person.

Not included, to keep the repo small and avoid copying other people's posts: the raw gist files, the fetched quoted-tweet context (`data/context.jsonl`) and downloaded images. Run `merge.py` and `enrich.py` to rebuild them.

## Limits

- No replies or reposts, and uneven coverage by year.
- Images are only read for 2025. Before that, posts that are only an image or video are mostly unclassified. In a spot check of 24 image labels, 20 looked right, 3 could not be judged from dark video frames and 1 looked wrong.
- The comparison labels were made by Claude Opus 5.5, not by a person.
