import os
import re
from fetch_articles import fetch_all_articles
from convert_to_markdown import html_to_markdown

OUTPUT_DIR = "docs_md"

def slugify(title):
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug

def save_one_article(article):
    title = article["title"]
    html_body = article["body"]
    url = article["html_url"]

    markdown_body = html_to_markdown(html_body)

    full_content = f"# {title}\n\nArticle URL: {url}\n\n{markdown_body}"

    filename = slugify(title) + ".md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)

    return filepath

if __name__ == "__main__":
    articles = fetch_all_articles()

    print(f"\nBắt đầu convert {len(articles)} bài viết...")

    for i, article in enumerate(articles, start=1):
        saved_path = save_one_article(article)
        print(f"[{i}/{len(articles)}] Đã lưu: {saved_path}")

    print("\n=== HOÀN TẤT TOÀN BỘ ===")