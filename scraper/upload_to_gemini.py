import os
import glob
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from google import genai

load_dotenv()

STORE_NAME_FILE = "store_name.txt"
MAX_WORKERS = 10

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_or_create_store():
    if os.path.exists(STORE_NAME_FILE):
        with open(STORE_NAME_FILE, "r") as f:
            store_name = f.read().strip()
        print(f"Found existing store: {store_name}, reusing it.")
        return store_name

    store = client.file_search_stores.create(
        config={"display_name": "optibot-clone-store"}
    )
    with open(STORE_NAME_FILE, "w") as f:
        f.write(store.name)

    print(f"Created new store: {store.name}")
    return store.name

def get_existing_display_names(store_name):
    """Get the list of filenames ALREADY in the Store, to avoid duplicate uploads."""
    existing = set()
    documents = client.file_search_stores.documents.list(parent=store_name)
    for doc in documents:
        existing.add(doc.display_name)
    return existing

def upload_single_file(filepath, store_name):
    operation = client.file_search_stores.upload_to_file_search_store(
        file=filepath,
        file_search_store_name=store_name,
        config={"display_name": os.path.basename(filepath)},
    )

    while not operation.done:
        time.sleep(1)
        operation = client.operations.get(operation)

    return filepath

def upload_all_files(store_name):
    md_files = glob.glob("docs_md/*.md")
    print(f"Found {len(md_files)} local files.")

    print("Checking which files are already in the Store...")
    existing_names = get_existing_display_names(store_name)
    print(f"Store currently has {len(existing_names)} files.")

    files_to_upload = [
        f for f in md_files
        if os.path.basename(f) not in existing_names
    ]
    skipped_count = len(md_files) - len(files_to_upload)

    print(f"Need to upload: {len(files_to_upload)} files. (Skipping {skipped_count} already present)\n")

    if not files_to_upload:
        print("No files need uploading. Done!")
        return

    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(upload_single_file, filepath, store_name): filepath
            for filepath in files_to_upload
        }

        for i, future in enumerate(as_completed(futures), start=1):
            filepath = futures[future]
            try:
                future.result()
                success_count += 1
                print(f"[{i}/{len(files_to_upload)}] ✅ Done: {filepath}")
            except Exception as e:
                fail_count += 1
                print(f"[{i}/{len(files_to_upload)}] ❌ Error: {filepath} - {e}")

    print(f"\n=== RESULT ===")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Skipped (already present): {skipped_count}")

def log_embedding_summary(store_name):
    print("\n=== EMBEDDING SUMMARY ===")

    documents = client.file_search_stores.documents.list(parent=store_name)

    total_files = 0
    total_bytes = 0

    for doc in documents:
        total_files += 1
        total_bytes += doc.size_bytes

    print(f"Total files embedded in store: {total_files}")
    print(f"Total indexed size: {total_bytes:,} bytes (~{total_bytes/1024:.1f} KB)")
    print("Note: the Gemini File Search API does not expose an endpoint to")
    print("retrieve a detailed chunk count per document — this is a platform")
    print("limitation (chunking is fully managed, not exposed).")

if __name__ == "__main__":
    store_name = get_or_create_store()
    print("Using store:", store_name)

    upload_all_files(store_name)
    log_embedding_summary(store_name)