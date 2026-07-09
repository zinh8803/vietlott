from bs4 import BeautifulSoup

def list_scripts():
    try:
        with open("scripts/bingo18_raw.html", "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "lxml")
        scripts = soup.find_all("script")
        print(f"Total scripts found: {len(scripts)}")
        for idx, s in enumerate(scripts):
            src = s.get("src")
            txt = s.get_text().strip()
            if src:
                print(f"[{idx}] Script SRC: '{src}'")
            else:
                print(f"[{idx}] Inline script (first 100 chars): '{txt[:100]}...'")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    list_scripts()
