import requests

BASE_URL = "https://support.optisigns.com/api/v2/help_center/articles.json"

def fetch_all_articles():
    all_articles = []
    url = BASE_URL

    while url:
        response = requests.get(url)
        data = response.json()

        all_articles.extend(data["articles"])
        print(f"Đã lấy trang này, tổng cộng hiện có: {len(all_articles)} bài")

        url = data["next_page"]  # trang kế tiếp, hoặc None nếu hết

    return all_articles

if __name__ == "__main__":
    articles = fetch_all_articles()
    print("\n=== HOÀN TẤT ===")
    print("Tổng số bài viết lấy được:", len(articles))