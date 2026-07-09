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

def analyze_power():
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655.html"
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "lxml")
        
        output = []
        output.append("POWER_655 Elements:")
        
        # 1. H5 headers
        h5_tags = soup.find_all("h5")
        for h5 in h5_tags:
            output.append(f"h5: '{h5.get_text(strip=True)}'")
            
        # 2. Bong tron
        spans = soup.find_all("span")
        for s in spans:
            cls = s.get("class")
            if cls:
                cls_str = " ".join(cls)
                if "bong_tron" in cls_str:
                    output.append(f"span class='{cls_str}': '{s.get_text(strip=True)}'")
                    
        with open("scripts/debug_power.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output))
            
        print("Successfully saved Power 6/55 analysis to scripts/debug_power.txt")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    analyze_power()
