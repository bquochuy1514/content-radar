# Content Radar

Small pipeline that scrapes a support knowledge base, converts articles to
clean Markdown, and syncs them into Gemini File Search as the knowledge
base for a support bot (basically an OptiBot clone). Includes a daily job
to keep it in sync with new/updated articles.

## Setup

1. Clone this repo
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.sample` to `.env` and fill in your `GEMINI_API_KEY` (free key at https://aistudio.google.com/api-keys)

## How to run locally

### 1. Scrape articles and convert to Markdown

```
python scraper/save_articles.py
```

Calls the support site's Zendesk API (paginated — it only returns 30
articles per page, and there are 406 total), pulls the `body` field (HTML)
from each article, converts it to Markdown with `markdownify`, and saves
one `.md` file per article into `docs_md/`.

### 2. Upload the Markdown files into the vector store

```
python scraper/upload_to_gemini.py
```

Creates (or reuses, if one already exists) a Gemini File Search Store, then
uploads every `.md` file into it via the API. Before uploading, it checks
which files are already in the store and skips those — I added this after
getting hit by a network timeout mid-upload a couple of times, which caused
duplicate uploads when I just reran the script from scratch.

Uploads run in parallel across 10 threads (`ThreadPoolExecutor`). The first
version uploaded one file at a time and waited for each to finish indexing
before moving to the next — with 406 files that was on track to take over
2 hours, so I switched to sending all uploads concurrently and polling for
completion afterward instead.

(TODO: `main.py` will wrap both scripts above into a single entry point,
once the daily job piece is done)

## Data source

- 406 articles pulled from the support site via the Zendesk Help Center API.
- 405/406 uploaded successfully (~99.75%). One article
  (`how-to-use-the-qr-scan-to-interact-touchless-qr-app.md`) consistently
  failed with `400 Bad Request: Upload has already been terminated`, even
  after several retries — looks like something specific to that request
  rather than a one-off network blip. Since the task only requires ≥30
  articles, I didn't dig further into it.

Upload log (final run):

```
Found 406 local files.
Need to upload: 406 files. (Skipping 0 already present)
...
=== RESULT ===
Success: 405
Failed: 1
Skipped (already present): 0
```

## Chunking strategy

Using Gemini File Search's default, fully-managed chunking — no custom
chunk size/overlap config. When a file is uploaded via
`upload_to_file_search_store()`, Gemini handles splitting it into chunks
and generating embeddings (`gemini-embedding-001`) on its own.

Went with the default instead of a custom strategy because:

- The API is built to abstract this away entirely — Google's own docs say
  it "automatically manages... optimal chunking strategies" — so rolling a
  custom chunker felt like added complexity without an obvious payoff here.
- The source articles are already short, self-contained docs (one topic per
  file), so a naive fixed-size chunker probably wouldn't split them much
  differently than the managed pipeline already does.

**Embedding log (final run):**

```
Total files embedded in store: 405
Total indexed size: 1,887,195 bytes (~1843.0 KB)
```

**On chunk-count logging specifically:** I initially assumed I could just
call some `chunks.list()` endpoint to get an exact chunk count per file,
but it turns out Gemini actually has two separate, unrelated APIs here:

- The older Semantic Retriever API (`corpora/*/documents/*/chunks`), where
  you create and manage chunks yourself via `chunks.create` /
  `chunks.batchCreate` — chunk-level data is naturally available there
  because you're the one creating the chunks.
- The newer File Search Tool (`fileSearchStores/*`), which is what this
  project uses (per the task's suggested Gemini equivalent). Chunking here
  is fully automatic and deliberately not exposed through any list/count
  API — chunk info only shows up transiently in `grounding_metadata` when
  you actually query the store, scoped to whatever chunks were retrieved
  for that one query, not a persistent total.

So for this project, exact chunk counts aren't retrievable through the API
being used. I'm logging file-level metrics instead (file count + total
indexed bytes), which is the most granular data actually available here.

## Daily job logs

(TODO: fill in after deploying the daily job)

## Screenshot

(TODO: add screenshot of the assistant answering with citations, once the
system prompt / assistant part is done)
