import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

def save_table_html():
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645.html"
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table")
        if table:
            with open("scripts/table_structure.html", "w", encoding="utf-8") as f:
                f.write(table.prettify())
            print("Successfully saved table HTML to scripts/table_structure.html")
        else:
            print("No table found")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    save_table_html()
