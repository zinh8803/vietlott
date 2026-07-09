import httpx
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

def analyze_js():
    url = "https://vietlott.vn/EX.js"
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True)
        js_content = resp.text
        print(f"JS Length: {len(js_content)}")
        
        # Luu file JS de check
        with open("scripts/ex_js_raw.js", "w", encoding="utf-8") as f:
            f.write(js_content)
            
        # Tim cac tu khoa lien quan
        keywords = ["bingo", "bingo18", "645", "655", "PrevNext", "ajax", "GetResult", "Post", "url:"]
        results = []
        for kw in keywords:
            matches = [m.start() for m in re.finditer(kw, js_content, re.IGNORECASE)]
            results.append(f"- Keyword '{kw}': found {len(matches)} matches")
            
        print("\n".join(results))
        
        # In ra cac dong co chua tu khoa 'bingo'
        lines = js_content.splitlines()
        bingo_lines = []
        for i, line in enumerate(lines):
            if "bingo" in line.lower():
                bingo_lines.append(f"Line {i+1}: {line.strip()[:200]}")
                
        print("\nLines containing 'bingo':")
        for bl in bingo_lines[:30]:
            print(bl)
            
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    analyze_js()
