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

def check_html():
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645.html"
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True)
        html = resp.text
        soup = BeautifulSoup(html, "lxml")
        
        # In do dai HTML
        print(f"HTML Length: {len(html)}")
        
        # Tim cac classes pho bien hoac cac the table, div co the chua thong tin
        print("Checking potential elements:")
        for selector in ["div.box-number-result", "div.result-number", "div.kqxs-result", "table", "tr", ".day_quay_so", ".live-result"]:
            found = soup.select(selector)
            print(f"- Selector '{selector}': found {len(found)}")
            
        # Neu co table, in ra mot vai class cua no
        tables = soup.find_all("table")
        for idx, table in enumerate(tables[:3]):
            print(f"Table {idx} classes: {table.get('class')}")
            
        # In ra 500 ky tu dau tien va cuoi cung cua body
        if soup.body:
            body_text = soup.body.get_text()
            print("\nFirst 300 chars of body text:")
            print(body_text[:300].strip())
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check_html()
