"""Vietlott crawler - scrape kết quả từ vietlott.vn.

Hỗ trợ Mega 6/45 và Power 6/55.
Crawler là idempotent: cùng draw_no chạy nhiều lần chỉ update 1 bản ghi.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy import insert as sa_insert

from app.db.models import Draw

# URLs chính thức vietlott.vn (dùng trang kết quả cũ có cấu trúc h5 + bong_tron)
PRODUCT_URLS = {
    "MEGA_645": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645.html",
    "POWER_655": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655.html",
    "BINGO18": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/view-detail-bingo18-result",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


def _parse_date(raw: str) -> Optional[date]:
    """Thử parse nhiều định dạng ngày."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_draw_page(html: str, product_code: str) -> list[dict]:
    """Parse trang kết quả vietlott.vn, trả danh sách record thô."""
    soup = BeautifulSoup(html, "lxml")
    records: list[dict] = []

    # 1. Thử parse theo giao diện hiện tại của Vietlott (hiển thị kỳ quay mới nhất trên trang)
    try:
        h5_tags = soup.find_all("h5")
        draw_no = None
        draw_date = None
        for h5 in h5_tags:
            txt = h5.get_text(strip=True)
            # Loại bỏ tất cả khoảng trắng để match regex dễ dàng hơn
            txt_clean = re.sub(r"\s+", "", txt)
            # Match "Kỳ quay thưởng #01520 ngày 07/06/2026" hoặc "Kỳ quay thưởng#01355ngày06/06/2026"
            m = re.search(r"Kỳquaythưởng#?(\d+)ngày([\d/]+)", txt_clean, re.IGNORECASE)
            if m:
                draw_no = int(m.group(1))
                draw_date = _parse_date(m.group(2))
                break

        # Tìm các quả bóng số (thẻ span có class chứa 'bong_tron')
        # MEGA_645: class=['bong_tron'], POWER_655: class=['bong_tron', 'small']
        # Chỉ lấy balls của kỳ quay mới nhất (nằm trong block đầu tiên)
        # Giới hạn số ball: MEGA=6, POWER=7 (6 chính + 1 bonus)
        balls = [
            s for s in soup.find_all("span")
            if s.get("class") and any("bong_tron" in c for c in s.get("class"))
        ]
        # Lọc chỉ lấy số ball cần thiết (tránh bị nhiều block ảnh hưởng)
        max_balls = 7 if product_code == "POWER_655" else 6
        balls = balls[:max_balls]

        if draw_no is not None and draw_date is not None and len(balls) >= 6:
            raw_numbers = [int(b.get_text(strip=True)) for b in balls]
            
            if product_code == "POWER_655" and len(balls) >= 7:
                # Quả bóng có class 'active' là bonus_number (Power 6/55)
                bonus_el = None
                for b in balls:
                    if any("active" in c for c in b.get("class", [])):
                        bonus_el = b
                        break
                if bonus_el:
                    bonus = int(bonus_el.get_text(strip=True))
                    # Loại bỏ bonus_el trước khi lấy 6 số chính
                    main_vals = [int(b.get_text(strip=True)) for b in balls if b is not bonus_el][:6]
                else:
                    # Fallback: số cuối cùng là bonus
                    bonus = raw_numbers[-1]
                    main_vals = raw_numbers[:6]
                main_numbers = sorted(main_vals)
            else:
                main_numbers = sorted(raw_numbers[:6])
                bonus = None

            records.append({
                "product_code": product_code,
                "draw_no": draw_no,
                "draw_date": draw_date,
                "n1": main_numbers[0],
                "n2": main_numbers[1],
                "n3": main_numbers[2],
                "n4": main_numbers[3],
                "n5": main_numbers[4],
                "n6": main_numbers[5],
                "bonus_number": bonus,
                "raw_payload": {"raw_numbers": raw_numbers},
            })
            logger.info(f"Parse thành công theo giao diện mới: Kỳ #{draw_no} ngày {draw_date}")
    except Exception as exc:
        logger.warning(f"Lỗi parse theo giao diện mới: {exc}")

    # 2. Nếu không tìm được bản ghi nào theo giao diện mới, thử fallback theo cấu trúc cũ
    if not records:
        rows = soup.select("div.box-number-result, div.result-number, div.kqxs-result")
        if not rows:
            rows = soup.select("tr[data-id], .prize-result")

        for row in rows:
            try:
                draw_no_el = row.select_one("[data-id], .draw-no, .kq-id")
                date_el = row.select_one(".draw-date, .date, .kq-date")
                numbers_el = row.select_all(".ball, .number-ball, span.ball-number")

                if not numbers_el:
                    text = row.get_text(separator=" ")
                    nums = re.findall(r"\b(\d{2})\b", text)
                    numbers_el = None
                    raw_numbers = [int(n) for n in nums]
                else:
                    raw_numbers = [int(el.get_text(strip=True)) for el in numbers_el]

                if len(raw_numbers) < 6:
                    continue

                main_numbers = sorted(raw_numbers[:6])
                bonus = raw_numbers[6] if (product_code == "POWER_655" and len(raw_numbers) > 6) else None

                draw_no = None
                if draw_no_el:
                    m = re.search(r"\d+", draw_no_el.get_text())
                    if m:
                        draw_no = int(m.group())

                draw_date = None
                if date_el:
                    draw_date = _parse_date(date_el.get_text())

                if draw_no is None or draw_date is None:
                    continue

                records.append({
                    "product_code": product_code,
                    "draw_no": draw_no,
                    "draw_date": draw_date,
                    "n1": main_numbers[0],
                    "n2": main_numbers[1],
                    "n3": main_numbers[2],
                    "n4": main_numbers[3],
                    "n5": main_numbers[4],
                    "n6": main_numbers[5],
                    "bonus_number": bonus,
                    "raw_payload": {"raw_numbers": raw_numbers},
                })
            except Exception as exc:
                logger.warning(f"Lỗi parse row cũ: {exc}")

    return records


def _upsert_draw(db: Session, record: dict) -> Draw:
    """Insert hoặc update bản ghi draw (idempotent)."""
    from sqlalchemy import select
    existing = db.execute(
        select(Draw).where(
            Draw.product_code == record["product_code"],
            Draw.draw_no == record["draw_no"],
        )
    ).scalar_one_or_none()

    if existing:
        for k, v in record.items():
            setattr(existing, k, v)
        db.flush()
        return existing
    else:
        draw = Draw(**record)
        db.add(draw)
        db.flush()
        return draw


def sync_draws(
    db: Session,
    product_code: str,
    from_date: Optional[date] = None,
    force: bool = False,
    timeout: float = 30.0,
    count: int = 1,
) -> list[Draw]:
    """Đồng bộ kết quả kỳ quay từ vietlott.vn.

    Args:
        db: SQLAlchemy session.
        product_code: "MEGA_645" hoặc "POWER_655".
        from_date: Chỉ lấy từ ngày này (optional).
        force: Nếu True, cập nhật lại bản ghi đã có.
        timeout: HTTP timeout giây.
        count: Số lượng kỳ quay thực tế cần crawl lùi từ kỳ mới nhất.

    Returns:
        Danh sách Draw đã upsert.
    """
    url = PRODUCT_URLS.get(product_code)
    if not url:
        raise ValueError(f"Không hỗ trợ product_code={product_code!r}")

    logger.info(f"Crawling {product_code} từ {url}")

    try:
        with httpx.Client(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
            source_url = str(resp.url)
    except httpx.HTTPError as exc:
        logger.error(f"HTTP error khi crawl {product_code}: {exc}")
        raise

    records = _parse_draw_page(html, product_code)
    logger.info(f"Parse được {len(records)} kết quả cho {product_code}")

    draw_nos_to_crawl = []
    if records and product_code in ("MEGA_645", "POWER_655"):
        latest_draw_no = records[0]["draw_no"]
        from sqlalchemy import select
        existing_draw_nos = set(db.scalars(
            select(Draw.draw_no).where(Draw.product_code == product_code)
        ).all())
        
        # 1. Tìm các kỳ quay bị thiếu trong khoảng lookback (300 kỳ quay gần nhất)
        lookback = 300
        missing_in_lookback = [
            d for d in range(max(1, latest_draw_no - lookback), latest_draw_no)
            if d not in existing_draw_nos
        ]
        
        # 2. Lấy danh sách kỳ quay lùi theo số lượng 'count' được yêu cầu
        requested_nos = [
            latest_draw_no - i for i in range(1, count)
            if (latest_draw_no - i) > 0
        ]
        
        # Gộp danh sách, loại bỏ trùng lặp và sắp xếp giảm dần (mới nhất lên trước)
        draw_nos_to_crawl = sorted(list(set(missing_in_lookback + requested_nos)), reverse=True)

    if draw_nos_to_crawl and records and product_code in ("MEGA_645", "POWER_655"):
        latest_draw_no = records[0]["draw_no"]
        logger.info(f"Crawl lùi bổ sung các kỳ: {draw_nos_to_crawl[:10]}... (Tổng cộng: {len(draw_nos_to_crawl)} kỳ)")

        try:
            render_url = "https://vietlott.vn/ajaxpro/Vietlott.Utility.WebEnvironments,Vietlott.Utility.ashx"
            ajax_headers = {
                **HEADERS,
                "Content-Type": "text/plain; charset=utf-8",
                "X-AjaxPro-Method": "ServerSideFrontEndCreateRenderInfo"
            }
            import json
            with httpx.Client(timeout=timeout) as client:
                resp_render = client.post(render_url, headers=ajax_headers, content=json.dumps({"SiteId": "main.frontend.vi"}))
                resp_render.raise_for_status()
                oRenderInfo = json.loads(resp_render.text)["value"]
                oRenderInfo["SiteLang"] = "vi"

                if product_code == "MEGA_645":
                    draw_url = "https://vietlott.vn/ajaxpro/Vietlott.PlugIn.WebParts.Game645ResultDetailWebPart,Vietlott.PlugIn.WebParts.ashx"
                else:
                    draw_url = "https://vietlott.vn/ajaxpro/Vietlott.PlugIn.WebParts.Game655ResultDetailWebPart,Vietlott.PlugIn.WebParts.ashx"

                ajax_headers["X-AjaxPro-Method"] = "ServerSideDrawResult"

                for prev_draw_no in draw_nos_to_crawl:
                    if prev_draw_no <= 0:
                        break
                    draw_id_str = f"{prev_draw_no:05d}"
                    payload_draw = {
                        "ORenderInfo": oRenderInfo,
                        "Key": "7e9628ea",
                        "DrawId": draw_id_str
                    }
                    resp_draw = client.post(draw_url, headers=ajax_headers, content=json.dumps(payload_draw))
                    if resp_draw.status_code == 200:
                        draw_data = json.loads(resp_draw.text)["value"]
                        html_content = draw_data.get("RetExtraParam1")
                        if html_content:
                            prev_records = _parse_draw_page(html_content, product_code)
                            if prev_records:
                                records.extend(prev_records)
                                logger.info(f"Crawl thành công kỳ #{prev_draw_no}")
                            else:
                                logger.warning(f"Không thể parse dữ liệu kỳ #{prev_draw_no}")
                        else:
                            logger.warning(f"Không nhận được nội dung kỳ #{prev_draw_no}")
                    else:
                        logger.warning(f"Lỗi gọi AjaxPro cho kỳ #{prev_draw_no}: {resp_draw.status_code}")
        except Exception as exc:
            logger.error(f"Lỗi khi crawl dữ liệu lịch sử qua AjaxPro: {exc}")

    draws: list[Draw] = []
    for rec in records:
        rec["source_url"] = source_url
        if from_date and rec["draw_date"] < from_date:
            continue
        draw = _upsert_draw(db, rec)
        draws.append(draw)

    db.commit()
    logger.info(f"Upsert {len(draws)} draws vào DB")

    # Tự động đối chiếu các predictions đang pending sau khi có kết quả mới
    try:
        from app.reconcile.reconcile_results import reconcile_pending
        reconciled = reconcile_pending(db, product_code)
        if reconciled:
            logger.info(f"Tự động đối chiếu thành công {len(reconciled)} predictions cho {product_code}")
    except Exception as exc:
        logger.error(f"Lỗi khi tự động đối chiếu predictions: {exc}")

    return draws


def seed_sample_draws(db: Session, product_code: str, count: int = 50) -> list[Draw]:
    """Tạo dữ liệu mẫu ngẫu nhiên để demo (không cần mạng).

    Lịch sử quay giả lập từ 2022 đến nay.
    """
    import random
    from datetime import timedelta

    draws: list[Draw] = []
    base_date = date(2022, 1, 5)  # Thứ Tư đầu tiên 2022

    if product_code == "BINGO18":
        # Bingo18 quay số hàng ngày, mô phỏng mỗi ngày 1 kỳ (hoặc tăng ngày dần)
        for i in range(count):
            draw_date = base_date + timedelta(days=i)
            draw_no = 20000 + i
            # Chọn ngẫu nhiên 3 số từ 1 đến 6 (các số này có thể lặp lại!)
            numbers = sorted([random.randint(1, 6) for _ in range(3)])
            rec = {
                "product_code": product_code,
                "draw_no": draw_no,
                "draw_date": draw_date,
                "n1": numbers[0],
                "n2": numbers[1],
                "n3": numbers[2],
                "n4": 0,
                "n5": 0,
                "n6": 0,
                "bonus_number": None,
                "source_url": "seed",
                "raw_payload": {"seed": True},
            }
            draw = _upsert_draw(db, rec)
            draws.append(draw)
    else:
        SPACE = 45 if product_code == "MEGA_645" else 55
        # Bước ngày: Mega = 3 ngày (Wed/Fri/Sun), Power = 3 ngày (Tue/Thu/Sat)
        step = 3

        for i in range(count):
            draw_date = base_date + timedelta(days=i * step)
            draw_no = 1000 + i
            numbers = sorted(random.sample(range(1, SPACE + 1), 6))
            bonus = random.randint(1, 45) if product_code == "POWER_655" else None
            rec = {
                "product_code": product_code,
                "draw_no": draw_no,
                "draw_date": draw_date,
                "n1": numbers[0],
                "n2": numbers[1],
                "n3": numbers[2],
                "n4": numbers[3],
                "n5": numbers[4],
                "n6": numbers[5],
                "bonus_number": bonus,
                "source_url": "seed",
                "raw_payload": {"seed": True},
            }
            draw = _upsert_draw(db, rec)
            draws.append(draw)

    db.commit()
    logger.info(f"Seeded {len(draws)} draws cho {product_code}")
    return draws
