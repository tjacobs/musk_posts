# Musk Posts

What Elon Musk posts about, by year (2012 to 2025). Each post is labeled with one of 18 topics by Claude Haiku. The topics roll up into 8 categories: Companies, Humor, Science, News, Media, Politics, Economy and Unclassified.

The finished report is `index.html`, a self-contained page with a stacked bar chart by category, a sortable grid of all 18 topics, and an example post for each bar section.

## Data

18,390 posts and quote tweets from @elonmusk, June 2010 to December 10, 2025, merged and de-duplicated from two public files in [this gist](https://gist.github.com/j4ckxyz/1518890aa6d319d23a516bf14240d2b2). The page charts 2012 onward (18,353 posts).

The archive has no replies or plain reposts, so it is a fraction of everything he posted. Outside counts put 2018 to 2021 at about 2,300 to 3,400 posts a year against 425 to 434 here.

## Method

1. Merge the two gist files into `data/tweets.csv` with `scripts/merge.py`.
2. Fetch the tweet each post quotes, plus any link title, from X's public embed service with `scripts/enrich.py`, so short reactions can be read in context.
3. Send batches of 100 posts to Claude Haiku through the `claude` command-line tool with `scripts/classify.py`, which writes `data/labels/`. The topic list and tie-break rules are in `categories.md`.
4. Build `data/labeled_tweets.csv` and `data/summary.json` with `scripts/aggregate.py`.
5. Fill `scripts/page_template.html` and write `index.html` with `scripts/build_page.py`.
6. Score the labels against `data/validation_labels.json` with `scripts/compare.py`. That file holds 200 posts (150 random, 50 from before 2022) labeled separately by Claude, with no person reviewing them. Haiku matched on the same topic 86% of the time and the same category 90% of the time.

Not included, to keep the repo small and avoid copying other people's posts: the raw gist files, the fetched quoted-tweet context (`data/context.jsonl`) and downloaded images. Run `merge.py` and `enrich.py` to rebuild them.

## Limits

- No replies or reposts, and uneven coverage by year.
- Photos and videos are not seen by the classifier, so posts that are only an image or video are mostly unclassified.
- The comparison labels were made by Claude, not by a person.
