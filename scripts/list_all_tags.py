from bs4 import BeautifulSoup

def list_all_tags():
    try:
        with open("scripts/bingo18_raw.html", "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "lxml")
        
        output = []
        for tag in soup.find_all(True):
            cls = " ".join(tag.get("class", []))
            id_val = tag.get("id", "")
            text = tag.get_text(separator=" ", strip=True)
            if text:
                # Rut ngan text neu dai qua
                text_snippet = text if len(text) <= 80 else text[:80] + "..."
                output.append(f"<{tag.name} class='{cls}' id='{id_val}'>: '{text_snippet}'")
            else:
                output.append(f"<{tag.name} class='{cls}' id='{id_val}'> [EMPTY]")
                
        with open("scripts/all_tags.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print("Successfully written all tags to scripts/all_tags.txt")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    list_all_tags()
