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

def download_mc():
    url = "https://www.minhchinh.com/xo-so-bingo18.html"
    try:
        print(f"Downloading: {url}")
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True)
        print(f"Status: {resp.status_code}, length: {len(resp.text)}")
        
        soup = BeautifulSoup(resp.text, "lxml")
        with open("scripts/minhchinh_bingo18_real.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("Saved HTML to scripts/minhchinh_bingo18_real.html")
        
        # Xem co chua 'bingo18' va cac balls/dices khong
        print("Checking text occurrences:")
        print("Contains 'bingo18':", "bingo18" in resp.text.lower())
        
        # Tim kiem cac the table
        tables = soup.find_all("table")
        print(f"Found {len(tables)} tables")
        for idx, table in enumerate(tables):
            cls = " ".join(table.get("class", []))
            id_val = table.get("id", "")
            txt = table.get_text(separator=" ", strip=True)[:100]
            print(f"- Table {idx} (class='{cls}', id='{id_val}'): '{txt}'")
            
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    download_mc()
