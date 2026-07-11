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
        print(f"Đã tìm thấy store cũ: {store_name}, tái sử dụng.")
        return store_name

    store = client.file_search_stores.create(
        config={"display_name": "optibot-clone-store"}
    )
    with open(STORE_NAME_FILE, "w") as f:
        f.write(store.name)

    print(f"Đã tạo store mới: {store.name}")
    return store.name

def get_existing_display_names(store_name):
    """Lấy danh sách tên file ĐÃ CÓ SẴN trong Store, để tránh upload trùng."""
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
    print(f"Tìm thấy {len(md_files)} file local.")

    print("Đang kiểm tra file nào đã có sẵn trong Store...")
    existing_names = get_existing_display_names(store_name)
    print(f"Store hiện có {len(existing_names)} file.")

    files_to_upload = [
        f for f in md_files
        if os.path.basename(f) not in existing_names
    ]
    skipped_count = len(md_files) - len(files_to_upload)

    print(f"Cần upload thêm: {len(files_to_upload)} file. (Bỏ qua {skipped_count} file đã có sẵn)\n")

    if not files_to_upload:
        print("Không có file nào cần upload thêm. Xong!")
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
                print(f"[{i}/{len(files_to_upload)}] ✅ Xong: {filepath}")
            except Exception as e:
                fail_count += 1
                print(f"[{i}/{len(files_to_upload)}] ❌ Lỗi: {filepath} - {e}")

    print(f"\n=== KẾT QUẢ ===")
    print(f"Thành công: {success_count}")
    print(f"Thất bại: {fail_count}")
    print(f"Bỏ qua (đã có sẵn): {skipped_count}")

def log_embedding_summary(store_name):
    print("\n=== TỔNG KẾT EMBEDDING ===")

    documents = client.file_search_stores.documents.list(parent=store_name)

    total_files = 0
    total_bytes = 0

    for doc in documents:
        total_files += 1
        total_bytes += doc.size_bytes

    print(f"Tổng số file đã embed trong Store: {total_files}")
    print(f"Tổng dung lượng đã embed: {total_bytes:,} bytes (~{total_bytes/1024:.1f} KB)")
    print("Lưu ý: Gemini File Search API không cung cấp endpoint để đếm số")
    print("chunk chi tiết cho mỗi document — đây là giới hạn của nền tảng")
    print("(chunking hoàn toàn managed, không lộ ra ngoài).")

if __name__ == "__main__":
    store_name = get_or_create_store()
    print("Store đang dùng:", store_name)

    upload_all_files(store_name)
    log_embedding_summary(store_name)