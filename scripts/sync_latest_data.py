"""Script dong bo du lieu Vietlott moi nhat tu vietlott.vn."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app.db.database import SessionLocal
from app.crawlers.vietlott_crawler import sync_draws

def main():
    db = SessionLocal()
    try:
        print("Dong bo du lieu MEGA_645 tu vietlott.vn...")
        mega_draws = sync_draws(db, "MEGA_645", force=True)
        print(f"Thanh cong! Da dong bo {len(mega_draws)} ky quay MEGA_645.")
        if mega_draws:
            latest = max(mega_draws, key=lambda x: x.draw_no)
            print(f" Ky moi nhat: Ky #{latest.draw_no} ngay {latest.draw_date} - So: {latest.n1}, {latest.n2}, {latest.n3}, {latest.n4}, {latest.n5}, {latest.n6}")
        else:
            print("Khong tim thay ket qua nao cho MEGA_645.")
        
        print("\nDong bo du lieu POWER_655 tu vietlott.vn...")
        power_draws = sync_draws(db, "POWER_655", force=True)
        print(f"Thanh cong! Da dong bo {len(power_draws)} ky quay POWER_655.")
        if power_draws:
            latest = max(power_draws, key=lambda x: x.draw_no)
            print(f" Ky moi nhat: Ky #{latest.draw_no} ngay {latest.draw_date} - So: {latest.n1}, {latest.n2}, {latest.n3}, {latest.n4}, {latest.n5}, {latest.n6} [Bonus: {latest.bonus_number}]")
        else:
            print("Khong tim thay ket qua nao cho POWER_655.")
    except Exception as e:
        print(f"Loi khi dong bo du lieu: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
