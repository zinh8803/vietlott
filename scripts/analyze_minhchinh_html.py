from bs4 import BeautifulSoup
import re

def analyze():
    try:
        with open("scripts/minhchinh_bingo18.html", "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "lxml")
        
        output = []
        tables = soup.find_all("table")
        output.append(f"Total tables: {len(tables)}")
        
        for idx, t in enumerate(tables):
            cls = " ".join(t.get("class", []))
            id_val = t.get("id", "")
            # Lay 100 ky tu text dau cua table
            txt = t.get_text(separator=" ", strip=True)
            txt_snippet = txt[:150] + "..." if len(txt) > 150 else txt
            output.append(f"Table {idx} class='{cls}' id='{id_val}': {txt_snippet}")
            
            # Neu table co các hang, in ra 5 hang dau
            rows = t.find_all("tr")
            for r_idx, r in enumerate(rows[:5]):
                r_txt = r.get_text(separator=" | ", strip=True)
                output.append(f"  Row {r_idx}: {r_txt[:200]}")
                
        with open("scripts/minhchinh_tables.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print("Saved table analysis to scripts/minhchinh_tables.txt")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    analyze()
