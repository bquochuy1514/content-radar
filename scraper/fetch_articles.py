import requests

BASE_URL = "https://support.optisigns.com/api/v2/help_center/articles.json"

def fetch_all_articles():
    all_articles = []
    url = BASE_URL

    while url:
        response = requests.get(url)
        data = response.json()

        all_articles.extend(data["articles"])
        print(f"Fetched this page, total so far: {len(all_articles)} articles")

        url = data["next_page"]  # next page, or None if there are no more

    return all_articles

if __name__ == "__main__":
    articles = fetch_all_articles()
    print("\n=== DONE ===")
    print("Total articles fetched:", len(articles))