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

def download_html():
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/view-detail-bingo18-result"
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "lxml")
        
        print(f"HTML Length: {len(resp.text)}")
        h5_tags = soup.find_all("h5")
        for h5 in h5_tags[:5]:
            print(f"h5: '{h5.get_text(strip=True)}'")
            
        with open("scripts/bingo18_raw.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("Successfully saved raw HTML to scripts/bingo18_raw.html")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    download_html()
