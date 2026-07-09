import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

def download_proxy():
    url = "https://vietlott.vn/ajaxpro/Vietlott.PlugIn.WebParts.GameBingoResultDetailWebPart,Vietlott.PlugIn.WebParts.ashx"
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True)
        with open("scripts/bingo_proxy.js", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print(f"Proxy JS length: {len(resp.text)}")
        print("First 500 chars of proxy JS:")
        print(resp.text[:500])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    download_proxy()
