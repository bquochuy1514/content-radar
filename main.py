import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from scraper.fetch_articles import fetch_all_articles
from scraper.convert_to_markdown import html_to_markdown
from scraper.save_articles import slugify
from scraper.upload_to_gemini import get_or_create_store, client

STATE_FILE = "state.json"
DOCS_DIR = "docs_md"
MAX_WORKERS = 10

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def classify_articles(articles, old_state):
    """Stage 1: figure out which articles need add/update/skip, write Markdown for the ones that need processing."""
    to_process = []
    skipped_state = {}

    for article in articles:
        article_id = str(article["id"])
        title = article["title"]
        updated_at = article["updated_at"]
        previous = old_state.get(article_id)

        if previous and previous["updated_at"] == updated_at:
            skipped_state[article_id] = previous
            continue

        filename = slugify(title) + ".md"
        filepath = os.path.join(DOCS_DIR, filename)
        markdown_body = html_to_markdown(article["body"])
        full_content = f"# {title}\n\nArticle URL: {article['html_url']}\n\n{markdown_body}"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)

        to_process.append({
            "article_id": article_id,
            "filename": filename,
            "filepath": filepath,
            "updated_at": updated_at,
            "is_update": previous is not None,
            "old_document_name": previous.get("document_name") if previous else None,
        })

    return to_process, skipped_state

def upload_one(item, store_name):
    if item["old_document_name"]:
        try:
            client.file_search_stores.documents.delete(name=item["old_document_name"])
        except Exception:
            pass

    operation = client.file_search_stores.upload_to_file_search_store(
        file=item["filepath"],
        file_search_store_name=store_name,
        config={"display_name": item["filename"]},
    )
    while not operation.done:
        operation = client.operations.get(operation)

    document_name = operation.response.document_name if operation.response else None

    return {
        "article_id": item["article_id"],
        "updated_at": item["updated_at"],
        "filename": item["filename"],
        "document_name": document_name,
        "is_update": item["is_update"],
    }

def run_pipeline():
    print("=== Starting daily sync ===")

    store_name = get_or_create_store()
    old_state = load_state()

    print("Fetching latest articles...")
    articles = fetch_all_articles()

    print("\nClassifying articles: new / updated / unchanged...")
    to_process, new_state = classify_articles(articles, old_state)

    print(f"Need to process: {len(to_process)} articles. Unchanged (skip): {len(new_state)} articles.\n")

    added = updated = failed = 0

    if to_process:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(upload_one, item, store_name): item
                for item in to_process
            }

            for i, future in enumerate(as_completed(futures), start=1):
                item = futures[future]
                try:
                    result = future.result()
                    new_state[result["article_id"]] = {
                        "updated_at": result["updated_at"],
                        "filename": result["filename"],
                        "document_name": result["document_name"],
                    }
                    if result["is_update"]:
                        updated += 1
                        print(f"[{i}/{len(to_process)}] 🔄 Updated: {item['filename']}")
                    else:
                        added += 1
                        print(f"[{i}/{len(to_process)}] ➕ Added: {item['filename']}")
                except Exception as e:
                    failed += 1
                    print(f"[{i}/{len(to_process)}] ❌ Error: {item['filename']} - {e}")

    save_state(new_state)

    skipped = len(articles) - len(to_process)

    print(f"\n=== SYNC RESULT ===")
    print(f"Added: {added}")
    print(f"Updated: {updated}")
    print(f"Skipped (unchanged): {skipped}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    run_pipeline()