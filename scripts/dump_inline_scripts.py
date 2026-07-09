from bs4 import BeautifulSoup

def dump_scripts():
    try:
        with open("scripts/bingo18_raw.html", "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "lxml")
        scripts = soup.find_all("script")
        output = []
        for idx, s in enumerate(scripts):
            src = s.get("src")
            if not src:
                output.append(f"=== Script {idx} ===")
                output.append(s.get_text())
                output.append("\n" + "="*40 + "\n")
        
        with open("scripts/inline_scripts.js", "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print("Saved inline scripts to scripts/inline_scripts.js")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    dump_scripts()
