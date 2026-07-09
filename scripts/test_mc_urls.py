import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}

def test_urls():
    candidates = [
        "https://www.minhchinh.com/bingo18.html",
        "https://www.minhchinh.com/xo-so-bingo18.html",
        "https://www.minhchinh.com/vietlott/bingo18.html",
        "https://www.minhchinh.com/vietlott.html"
    ]
    for url in candidates:
        try:
            resp = httpx.get(url, headers=HEADERS, follow_redirects=False)
            print(f"URL: {url} -> Status: {resp.status_code}")
            if "location" in resp.headers:
                print(f"  Redirects to: {resp.headers['location']}")
        except Exception as e:
            print(f"URL: {url} -> Error: {e}")

if __name__ == "__main__":
    test_urls()
