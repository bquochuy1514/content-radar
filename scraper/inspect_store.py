import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

STORE_NAME_FILE = "store_name.txt"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

with open(STORE_NAME_FILE, "r") as f:
    store_name = f.read().strip()

print(f"Đang xem nội dung của Store: {store_name}\n")

documents = client.file_search_stores.documents.list(parent=store_name)

count = 0
for doc in documents:
    count += 1
    print(f"{count}. {doc.display_name}")
    if count == 1:
        print("\n--- Chi tiết đầy đủ của document đầu tiên (để xem có field gì) ---")
        print(doc)
        print("--- Hết chi tiết ---\n")

print(f"\nTổng số document trong Store: {count}")