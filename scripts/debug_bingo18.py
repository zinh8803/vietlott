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

def analyze_bingo18():
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/bingo18.html"
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "lxml")
        
        output = []
        output.append("BINGO18 Elements:")
        
        # 1. H5 headers
        h5_tags = soup.find_all("h5")
        for h5 in h5_tags:
            output.append(f"h5: '{h5.get_text(strip=True)}'")
            
        # 2. H4, H3 headers
        for tag in ["h4", "h3", "div", "span", "p"]:
            for t in soup.find_all(tag):
                cls = t.get("class")
                cls_str = " ".join(cls) if cls else ""
                txt = t.get_text(strip=True)
                if not txt:
                    continue
                if "bong_tron" in cls_str or "dice" in cls_str or "bingo" in cls_str.lower() or "trung-thuong" in cls_str.lower() or any(x in txt for x in ["Kỳ quay", "Kỳ", "ngày"]):
                    output.append(f"{tag} class='{cls_str}': '{txt[:200]}'")
                    
        with open("scripts/debug_bingo18.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output))
            
        print("Successfully saved Bingo18 analysis to scripts/debug_bingo18.txt")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    analyze_bingo18()
