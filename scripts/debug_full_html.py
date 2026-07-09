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

def analyze_full_html():
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645.html"
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "lxml")
        
        output = []
        output.append("Finding elements with classes related to balls:")
        all_elements = soup.find_all(True)
        for el in all_elements:
            cls = el.get("class")
            if cls:
                cls_str = " ".join(cls)
                if any(x in cls_str.lower() for x in ["ball", "number", "result", "trung-thuong", "kq", "draw", "ky", "bong_tron"]):
                    txt = el.get_text(separator=" ", strip=True)
                    if txt:
                        output.append(f"<{el.name} class='{cls_str}'>: '{txt}'")
            
            # Neu co ID lien quan
            id_val = el.get("id")
            if id_val and any(x in id_val.lower() for x in ["ball", "number", "result", "trung-thuong", "kq", "draw", "ky"]):
                txt = el.get_text(separator=" ", strip=True)
                output.append(f"<{el.name} id='{id_val}'>: '{txt}'")
        
        with open("scripts/debug_elements.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output))
            
        print("Successfully saved elements analysis to scripts/debug_elements.txt")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    analyze_full_html()
