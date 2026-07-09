import httpx
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

def analyze_date_and_draw():
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645.html"
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "lxml")
        
        output = []
        # Tim kiem ky quay va ngay trong text cua cac the h1, h2, h3, h4, h5, p, span, div
        for tag_name in ["h1", "h2", "h3", "h4", "h5", "p", "span", "div", "td"]:
            tags = soup.find_all(tag_name)
            for t in tags:
                text = t.get_text(separator=" ", strip=True)
                if not text:
                    continue
                # Neu chua ky quay hoac ngay thang
                if any(k in text for k in ["Kỳ", "kỳ", "Ky", "ky", "ngày", "Ngày", "ngay", "Ngay"]) or "/" in text or "-" in text:
                    # In ra tag class, id va text cua no
                    cls = " ".join(t.get("class", []))
                    id_val = t.get("id", "")
                    output.append(f"<{tag_name} class='{cls}' id='{id_val}'>: '{text}'")
                    
        with open("scripts/debug_date.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output))
            
        print("Successfully saved date analysis to scripts/debug_date.txt")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    analyze_date_and_draw()
