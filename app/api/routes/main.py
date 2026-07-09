"""API routes: tất cả internal endpoints + dashboard data."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import inspect, select, func, text

from app.db.database import get_db
from app.db.models import AppUser, Draw, Feature, Metric, Model, Prediction, RetrainJob, UserTicket
from app.core.config import get_settings

settings = get_settings()
router = APIRouter()


# ─── Schemas ───────────────────────────────────────────────────────────────

class SyncDrawsRequest(BaseModel):
    product_code: str = "MEGA_645"
    force: bool = False
    use_seed: bool = False  # Dùng seed data thay vì crawl thật
    count: int = 1          # Số lượng kỳ quay thực tế cần crawl lùi từ kỳ mới nhất
    auto_train_after_result: bool = False


class BuildFeaturesRequest(BaseModel):
    product_code: str = "MEGA_645"
    window_size: int = 20
    feature_version: str = "v1"


class TrainRequest(BaseModel):
    product_code: str = "MEGA_645"
    window_size: int = 20
    feature_version: str = "v1"
    use_celery: bool = False  # False = chạy sync (cho dev)


class TrainProductsRequest(BaseModel):
    product_codes: list[str] = ["MEGA_645", "POWER_655"]
    window_size: Optional[int] = None
    feature_version: str = "v1"
    force: bool = True
    use_celery: bool = False


class PredictRequest(BaseModel):
    product_code: str = "MEGA_645"
    request_type: str = "manual"
    random_sample: bool = False


class ReconcileRequest(BaseModel):
    product_code: str = "MEGA_645"
    auto_train_after_result: bool = False


class LearnFromResultsRequest(BaseModel):
    product_codes: list[str] = ["MEGA_645", "POWER_655"]
    sync_latest: bool = True
    count: int = 1
    window_size: Optional[int] = None
    feature_version: str = "v1"
    force_retrain: bool = False
    use_celery: bool = False


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateTicketRequest(BaseModel):
    user_id: int
    product_code: str = "MEGA_645"
    random_sample: bool = True


class UpdateUserLimitRequest(BaseModel):
    daily_ticket_limit: Optional[int] = None
    add_quota: int = 0
    unlock: bool = True


# ─── Crawler ───────────────────────────────────────────────────────────────

def _today() -> date:
    return date.today()


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def _verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        scheme, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return hmac.compare_digest(digest.hex(), expected)


def _ensure_auth_columns(db: Session) -> None:
    bind = db.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("app_users"):
        return
    columns = {col["name"] for col in inspector.get_columns("app_users")}
    if "password_hash" not in columns:
        db.execute(text("ALTER TABLE app_users ADD COLUMN password_hash VARCHAR(256) NULL"))
        db.commit()


def _ensure_demo_accounts(db: Session) -> None:
    _ensure_auth_columns(db)
    existing = db.execute(select(func.count()).select_from(AppUser)).scalar() or 0
    if existing:
        for username, default_password in (("admin", "admin123"), ("user_demo", "user123")):
            user = db.execute(select(AppUser).where(AppUser.username == username)).scalar_one_or_none()
            if user and not user.password_hash:
                user.password_hash = _hash_password(default_password)
        db.commit()
        return
    db.add_all([
        AppUser(username="user_demo", display_name="User Demo", password_hash=_hash_password("user123"), role="user", daily_ticket_limit=3),
        AppUser(username="admin", display_name="Admin", password_hash=_hash_password("admin123"), role="admin", daily_ticket_limit=999999),
    ])
    db.commit()


def _ticket_usage_today(db: Session, user_id: int) -> int:
    today = _today()
    return db.execute(
        select(func.count()).where(
            UserTicket.user_id == user_id,
            func.date(UserTicket.created_at) == today,
        )
    ).scalar() or 0


def _user_payload(db: Session, user: AppUser) -> dict[str, Any]:
    used_today = _ticket_usage_today(db, user.user_id)
    unlimited = user.role == "admin"
    remaining = None if unlimited else max(0, user.daily_ticket_limit - used_today)
    locked = not unlimited and used_today >= user.daily_ticket_limit
    return {
        "user_id": user.user_id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "daily_ticket_limit": user.daily_ticket_limit,
        "used_today": used_today,
        "remaining_today": remaining,
        "is_unlimited": unlimited,
        "is_locked": locked,
        "lock_date": user.lock_date.isoformat() if user.lock_date else None,
    }


@router.post("/api/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a normal user account."""
    _ensure_demo_accounts(db)
    username = req.username.strip().lower()
    display_name = req.display_name.strip()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username toi thieu 3 ky tu")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Mat khau toi thieu 6 ky tu")
    if not display_name:
        raise HTTPException(status_code=400, detail="Ten hien thi khong duoc de trong")

    existing = db.execute(select(AppUser).where(AppUser.username == username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Username da ton tai")

    user = AppUser(
        username=username,
        display_name=display_name,
        password_hash=_hash_password(req.password),
        role="user",
        daily_ticket_limit=3,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "ok", "user": _user_payload(db, user)}


@router.post("/api/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login local user/admin account."""
    _ensure_demo_accounts(db)
    username = req.username.strip().lower()
    user = db.execute(select(AppUser).where(AppUser.username == username)).scalar_one_or_none()
    if not user or not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Sai username hoac mat khau")
    return {"status": "ok", "user": _user_payload(db, user)}


@router.get("/api/users")
def list_app_users(db: Session = Depends(get_db)):
    """List local demo users with today's ticket quota."""
    _ensure_demo_accounts(db)
    users = db.execute(select(AppUser).order_by(AppUser.role, AppUser.user_id)).scalars().all()
    return [_user_payload(db, user) for user in users]


@router.get("/api/users/{user_id}/tickets")
def list_user_tickets(
    user_id: int,
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
):
    """List tickets generated by a user/admin."""
    _ensure_demo_accounts(db)
    user = db.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User khong ton tai")

    tickets = db.execute(
        select(UserTicket)
        .where(UserTicket.user_id == user_id)
        .order_by(UserTicket.created_at.desc())
        .limit(limit)
    ).scalars().all()

    return {
        "user": _user_payload(db, user),
        "data": [
            {
                "ticket_id": t.ticket_id,
                "prediction_id": t.prediction_id,
                "product_code": t.product_code,
                "predicted_draw_no": t.predicted_draw_no,
                "numbers": t.numbers_json,
                "created_at": t.created_at.isoformat(),
            }
            for t in tickets
        ],
    }


@router.post("/api/tickets")
def create_ticket(req: CreateTicketRequest, db: Session = Depends(get_db)):
    """Generate a lottery ticket while enforcing daily user quota."""
    _ensure_demo_accounts(db)
    user = db.get(AppUser, req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User khong ton tai")

    if req.product_code not in ("MEGA_645", "POWER_655", "BINGO18"):
        raise HTTPException(status_code=400, detail="Product khong hop le")

    used_today = _ticket_usage_today(db, user.user_id)
    if user.role != "admin" and used_today >= user.daily_ticket_limit:
        user.lock_date = _today()
        db.commit()
        raise HTTPException(
            status_code=403,
            detail={
                "code": "DAILY_LIMIT_EXCEEDED",
                "message": "Ban da het luot tao ve trong ngay. Vui long lien he admin de tang gioi han.",
                "user": _user_payload(db, user),
            },
        )

    from app.predict.generate_next_prediction import generate_next_prediction
    cfg = settings.products.get(req.product_code, {})
    number_space = cfg.get("number_space", 45)
    pred = generate_next_prediction(
        db,
        req.product_code,
        request_type="admin" if user.role == "admin" else "user",
        number_space=number_space,
        random_sample=req.random_sample,
    )
    if not pred:
        raise HTTPException(status_code=404, detail="Chua co champion model hoac draw data")

    ticket = UserTicket(
        user_id=user.user_id,
        prediction_id=pred.prediction_id,
        product_code=pred.product_code,
        predicted_draw_no=pred.predicted_draw_no,
        numbers_json=pred.top6_json,
    )
    db.add(ticket)
    if user.role != "admin" and used_today + 1 >= user.daily_ticket_limit:
        user.lock_date = _today()
    db.commit()
    db.refresh(ticket)

    return {
        "status": "ok",
        "ticket": {
            "ticket_id": ticket.ticket_id,
            "prediction_id": ticket.prediction_id,
            "product_code": ticket.product_code,
            "predicted_draw_no": ticket.predicted_draw_no,
            "numbers": ticket.numbers_json,
            "created_at": ticket.created_at.isoformat(),
        },
        "user": _user_payload(db, user),
    }


@router.patch("/api/admin/users/{user_id}/quota")
def update_user_quota(
    user_id: int,
    req: UpdateUserLimitRequest,
    db: Session = Depends(get_db),
):
    """Admin action: increase/set a user's daily ticket limit and unlock them."""
    _ensure_demo_accounts(db)
    user = db.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User khong ton tai")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Admin khong can gioi han")

    if req.daily_ticket_limit is not None:
        user.daily_ticket_limit = max(0, req.daily_ticket_limit)
    if req.add_quota:
        user.daily_ticket_limit = max(0, user.daily_ticket_limit + req.add_quota)
    if req.unlock:
        user.lock_date = None
    db.commit()

    return {"status": "ok", "user": _user_payload(db, user)}


# ─── Background Check & Sync Crawler ──────────────────────────────────────────

LAST_CRAWL_ATTEMPT: dict[str, float] = {}

def bg_sync_draws(product_code: str):
    """Hàm chạy ngầm cào kết quả từ vietlott.vn."""
    import time
    import traceback
    from loguru import logger
    from app.db.database import SessionLocal
    from app.crawlers.vietlott_crawler import sync_draws
    db = SessionLocal()
    try:
        logger.info(f"Bắt đầu cào dữ liệu ngầm cho {product_code}")
        sync_draws(db, product_code, count=1)
        logger.info(f"Hoàn thành cào dữ liệu ngầm cho {product_code}")
    except Exception as e:
        logger.error(f"Lỗi cào dữ liệu ngầm cho {product_code}: {e}\n{traceback.format_exc()}")
    finally:
        db.close()


@router.post("/api/crawler/check-and-sync-background")
def check_and_sync_background(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Kiểm tra xem đã cào dữ liệu mới nhất chưa, nếu chưa thì đẩy vào background queue cào ngầm."""
    import time
    from datetime import datetime, timedelta
    from loguru import logger
    
    now = datetime.now()
    results = {}
    
    for product_code in ("MEGA_645", "POWER_655", "BINGO18"):
        # Truy vấn kỳ quay mới nhất và kiểm tra xem có dữ liệu mẫu (seed) hay không
        latest_draw = db.execute(
            select(Draw)
            .where(Draw.product_code == product_code)
            .order_by(Draw.draw_no.desc())
        ).scalars().first()

        has_seed = False
        if latest_draw:
            has_seed = db.execute(
                select(Draw.draw_id)
                .where(Draw.product_code == product_code, Draw.source_url == "seed")
                .limit(1)
            ).scalar() is not None

        # Giới hạn tần suất check thực tế (bỏ qua nếu là dữ liệu mẫu hoặc trống để cào thật ngay)
        if not has_seed and latest_draw:
            throttle_seconds = 120 if product_code == "BINGO18" else 900
            last_attempt = LAST_CRAWL_ATTEMPT.get(product_code, 0.0)
            if time.time() - last_attempt < throttle_seconds:
                results[product_code] = {"status": "throttled", "message": "Vừa mới kiểm tra gần đây."}
                continue

        needs_crawl = False
        
        if not latest_draw or has_seed:
            needs_crawl = True
        else:
            latest_date = latest_draw.draw_date
            today = now.date()
            
            if product_code == "BINGO18":
                # Bingo18 quay từ 6h00 đến 21h55 hàng ngày.
                if today > latest_date:
                    if now.hour >= 6:
                        needs_crawl = True
                else:
                    # Cùng ngày hôm nay. Bingo18 quay 10 phút một lần.
                    if 6 <= now.hour <= 22:
                        time_since_ingested = now - latest_draw.ingested_at
                        if time_since_ingested > timedelta(minutes=15):
                            needs_crawl = True
                            
            elif product_code == "MEGA_645":
                # Mega quay thứ 4, thứ 6, chủ nhật lúc 18h00.
                if today > latest_date:
                    is_draw_day = now.weekday() in (2, 4, 6)
                    if is_draw_day and (now.hour > 18 or (now.hour == 18 and now.minute >= 30)):
                        needs_crawl = True
                    elif today - latest_date >= timedelta(days=2):
                        needs_crawl = True
                        
            elif product_code == "POWER_655":
                # Power quay thứ 3, thứ 5, thứ 7 lúc 18h00.
                if today > latest_date:
                    is_draw_day = now.weekday() in (1, 3, 5)
                    if is_draw_day and (now.hour > 18 or (now.hour == 18 and now.minute >= 30)):
                        needs_crawl = True
                    elif today - latest_date >= timedelta(days=2):
                        needs_crawl = True

        if needs_crawl:
            LAST_CRAWL_ATTEMPT[product_code] = time.time()
            try:
                # Thử đẩy vào hàng đợi Celery Queue
                from app.workers.tasks import sync_draws_task
                sync_draws_task.delay(product_code)
                results[product_code] = {"status": "queued", "message": "Đã thêm vào Celery Queue."}
                logger.info(f"Đã kích hoạt cào ngầm Celery Queue cho {product_code}")
            except Exception as e:
                # Fallback sang FastAPI BackgroundTasks nếu Celery/Redis chưa được cấu hình
                logger.warning(f"Không thể đẩy vào Celery Queue ({e}). Fallback sang FastAPI BackgroundTasks.")
                background_tasks.add_task(bg_sync_draws, product_code)
                results[product_code] = {"status": "queued", "message": "Đã thêm vào hàng đợi FastAPI (Fallback)."}
                logger.info(f"Kích hoạt cào ngầm FastAPI BackgroundTasks cho {product_code}")
        else:
            results[product_code] = {"status": "up-to-date", "message": "Dữ liệu hiện tại đã mới nhất."}

    return {"status": "ok", "check_results": results}


@router.post("/internal/crawler/sync-draws")
def sync_draws(req: SyncDrawsRequest, db: Session = Depends(get_db)):
    """Đồng bộ kết quả kỳ quay mới."""
    if req.use_seed:
        from app.crawlers.vietlott_crawler import seed_sample_draws
        draws = seed_sample_draws(db, req.product_code, count=550)
        return {"status": "seeded", "count": len(draws)}

    try:
        from app.crawlers.vietlott_crawler import sync_draws as _sync
        draws = _sync(db, req.product_code, force=req.force, count=req.count)
        response: dict[str, Any] = {"status": "ok", "synced": len(draws)}
        if req.auto_train_after_result and req.product_code in ("MEGA_645", "POWER_655"):
            from app.train.auto_retrain import auto_retrain_products_from_results
            response["auto_train"] = auto_retrain_products_from_results(
                db,
                products=[req.product_code],
                force=False,
            )[req.product_code]
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Features ──────────────────────────────────────────────────────────────

@router.post("/internal/features/build")
def build_features(req: BuildFeaturesRequest, db: Session = Depends(get_db)):
    """Sinh sliding-window features."""
    from app.features.sliding_window import build_all_features
    cfg = settings.products.get(req.product_code, {})
    number_space = cfg.get("number_space", 45)
    n_train, n_valid, n_test = build_all_features(
        db, req.product_code, req.window_size, req.feature_version,
        holdout_draws=settings.training.get("holdout_draws", 30),
        number_space=number_space,
    )
    return {"status": "ok", "n_train": n_train, "n_valid": n_valid, "n_test": n_test}


# ─── Training ──────────────────────────────────────────────────────────────

@router.post("/internal/train")
def train(req: TrainRequest, db: Session = Depends(get_db)):
    """Tạo training job (sync hoặc async qua Celery)."""
    if req.use_celery:
        from app.workers.tasks import train_all_task
        task = train_all_task.delay(req.product_code, req.window_size, req.feature_version)
        return {"status": "queued", "job_id": task.id}

    # Sync mode
    from app.train.train_baseline import train_baselines
    from app.train.train_lightgbm import train_lightgbm
    from app.train.train_xgboost import train_xgboost
    from app.train.select_champion import promote_champion

    baselines = train_baselines(db, req.product_code, req.feature_version, req.window_size,
                                artifact_root=settings.artifact_root)
    lgbm = train_lightgbm(db, req.product_code, req.feature_version, req.window_size,
                           artifact_root=settings.artifact_root)
    xgb = train_xgboost(db, req.product_code, req.feature_version, req.window_size,
                         artifact_root=settings.artifact_root)
    champion = promote_champion(db, req.product_code)

    return {
        "status": "ok",
        "baselines_trained": len(baselines),
        "lightgbm_model_id": lgbm.model_id if lgbm else None,
        "xgboost_model_id": xgb.model_id if xgb else None,
        "champion_model_id": champion.model_id if champion else None,
    }


# ─── Predict ───────────────────────────────────────────────────────────────

@router.post("/internal/train/products")
def train_products(req: TrainProductsRequest, db: Session = Depends(get_db)):
    """Train/retrain multiple products, especially Mega 6/45 and Power 6/55."""
    allowed = {"MEGA_645", "POWER_655"}
    product_codes = [p for p in req.product_codes if p in allowed]
    if not product_codes:
        raise HTTPException(status_code=400, detail="Chon MEGA_645 hoac POWER_655")

    if req.use_celery:
        from app.workers.tasks import auto_retrain_products_task
        task = auto_retrain_products_task.delay(
            product_codes,
            req.window_size,
            req.feature_version,
            req.force,
        )
        return {"status": "queued", "job_id": task.id, "product_codes": product_codes}

    from app.train.auto_retrain import auto_retrain_products_from_results
    results = auto_retrain_products_from_results(
        db,
        products=product_codes,
        window_size=req.window_size,
        feature_version=req.feature_version,
        force=req.force,
    )
    return {"status": "ok", "results": results}


@router.post("/internal/predict/next")
def predict_next(req: PredictRequest, db: Session = Depends(get_db)):
    """Sinh dự đoán kỳ kế tiếp."""
    from app.predict.generate_next_prediction import generate_next_prediction
    cfg = settings.products.get(req.product_code, {})
    number_space = cfg.get("number_space", 45)
    pred = generate_next_prediction(db, req.product_code, req.request_type, number_space, random_sample=req.random_sample)
    if not pred:
        raise HTTPException(status_code=404, detail="Không có champion model hoặc draw data")
    return {
        "prediction_id": pred.prediction_id,
        "product_code": pred.product_code,
        "predicted_draw_no": pred.predicted_draw_no,
        "top6": pred.top6_json,
        "probabilities": pred.probabilities_json,
        "generated_at": pred.generated_at.isoformat(),
    }


# ─── Reconcile ─────────────────────────────────────────────────────────────

@router.post("/internal/reconcile")
def reconcile(req: ReconcileRequest, db: Session = Depends(get_db)):
    """Đối chiếu prediction với kết quả chính thức."""
    from app.reconcile.reconcile_results import reconcile_pending
    reconciled = reconcile_pending(db, req.product_code)
    response: dict[str, Any] = {"status": "ok", "reconciled": len(reconciled)}
    if req.auto_train_after_result and req.product_code in ("MEGA_645", "POWER_655"):
        from app.train.auto_retrain import auto_retrain_products_from_results
        response["auto_train"] = auto_retrain_products_from_results(
            db,
            products=[req.product_code],
            reconciled_counts={req.product_code: len(reconciled)},
            force=False,
        )[req.product_code]
    return response


# ─── Models ────────────────────────────────────────────────────────────────

@router.post("/internal/train/learn-from-results")
def learn_from_results(req: LearnFromResultsRequest, db: Session = Depends(get_db)):
    """Sync latest official results, reconcile hits, then retrain 6/45 and 6/55."""
    allowed = {"MEGA_645", "POWER_655"}
    product_codes = [p for p in req.product_codes if p in allowed]
    if not product_codes:
        raise HTTPException(status_code=400, detail="Chon MEGA_645 hoac POWER_655")

    if req.use_celery:
        from app.workers.tasks import learn_from_results_task
        task = learn_from_results_task.delay(
            product_codes,
            req.sync_latest,
            req.count,
            req.window_size,
            req.feature_version,
            req.force_retrain,
        )
        return {"status": "queued", "job_id": task.id, "product_codes": product_codes}

    synced: dict[str, int] = {}
    reconciled_counts: dict[str, int] = {}

    if req.sync_latest:
        from app.crawlers.vietlott_crawler import sync_draws as _sync
        for product_code in product_codes:
            draws = _sync(db, product_code, count=req.count)
            synced[product_code] = len(draws)

    from app.reconcile.reconcile_results import reconcile_pending
    for product_code in product_codes:
        reconciled = reconcile_pending(db, product_code)
        reconciled_counts[product_code] = len(reconciled)

    from app.train.auto_retrain import auto_retrain_products_from_results
    train_results = auto_retrain_products_from_results(
        db,
        products=product_codes,
        reconciled_counts=reconciled_counts,
        window_size=req.window_size,
        feature_version=req.feature_version,
        force=req.force_retrain,
    )

    return {
        "status": "ok",
        "synced": synced,
        "reconciled": reconciled_counts,
        "train_results": train_results,
    }


@router.get("/internal/models")
def list_models(
    product_code: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Danh sách model/version."""
    q = select(Model)
    if product_code:
        q = q.where(Model.product_code == product_code)
    if status:
        q = q.where(Model.status == status)
    models = db.execute(q.order_by(Model.created_at.desc())).scalars().all()

    return [
        {
            "model_id": m.model_id,
            "model_name": m.model_name,
            "algorithm": m.algorithm,
            "product_code": m.product_code,
            "status": m.status,
            "metrics_summary": m.metrics_summary_json,
            "created_at": m.created_at.isoformat(),
            "promoted_at": m.promoted_at.isoformat() if m.promoted_at else None,
        }
        for m in models
    ]


@router.get("/internal/reports/backtests/{model_id}")
def get_backtest_report(model_id: int, db: Session = Depends(get_db)):
    """Đọc báo cáo backtest của một model."""
    model = db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model không tồn tại")

    metrics = db.execute(
        select(Metric)
        .where(Metric.model_id == model_id)
        .order_by(Metric.eval_scope, Metric.fold_no)
    ).scalars().all()

    return {
        "model_id": model_id,
        "model_name": model.model_name,
        "algorithm": model.algorithm,
        "status": model.status,
        "metrics": [
            {
                "metric_id": m.metric_id,
                "eval_scope": m.eval_scope,
                "fold_no": m.fold_no,
                "precision_at_6": m.precision_at_6,
                "log_loss": m.log_loss,
                "brier_score": m.brier_score,
                "metric_json": m.metric_json,
            }
            for m in metrics
        ],
    }


# ─── Dashboard Data APIs ────────────────────────────────────────────────────

@router.get("/api/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    """Dashboard: tóm tắt tổng quan."""
    result = {}
    for product in settings.products.keys():
        total_draws = db.execute(
            select(func.count()).where(Draw.product_code == product)
        ).scalar()

        # Champion
        champion = db.execute(
            select(Model)
            .where(Model.product_code == product, Model.status == "champion")
            .order_by(Model.created_at.desc())
        ).scalars().first()

        # Latest prediction
        latest_pred = db.execute(
            select(Prediction)
            .where(Prediction.product_code == product)
            .order_by(Prediction.generated_at.desc())
        ).scalars().first()

        # Live precision avg
        live_metrics = db.execute(
            select(func.avg(Metric.precision_at_6)).where(
                Metric.product_code == product,
                Metric.eval_scope == "live",
                Metric.precision_at_6.isnot(None),
            )
        ).scalar()

        result[product] = {
            "total_draws": total_draws,
            "champion": {
                "model_id": champion.model_id if champion else None,
                "model_name": champion.model_name if champion else None,
                "algorithm": champion.algorithm if champion else None,
                "metrics": champion.metrics_summary_json if champion else None,
            } if champion else None,
            "latest_prediction": {
                "prediction_id": latest_pred.prediction_id,
                "predicted_draw_no": latest_pred.predicted_draw_no,
                "top6": latest_pred.top6_json,
                "status": latest_pred.status,
                "generated_at": latest_pred.generated_at.isoformat(),
                "hit_count": latest_pred.hit_count_main,
            } if latest_pred else None,
            "live_precision_avg": float(live_metrics) if live_metrics else None,
        }

    return result


@router.get("/api/draws")
def list_draws(
    product_code: str = "MEGA_645",
    year: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Lịch sử kỳ quay."""
    from sqlalchemy import extract, cast, String, or_

    # Query distinct years available for this product
    years_db = db.execute(
        select(extract('year', Draw.draw_date))
        .where(Draw.product_code == product_code)
        .distinct()
        .order_by(extract('year', Draw.draw_date).desc())
    ).scalars().all()
    years = [int(y) for y in years_db if y is not None]

    # Build base query with product filter
    q = select(Draw).where(Draw.product_code == product_code)

    if year:
        q = q.where(extract('year', Draw.draw_date) == year)

    if search:
        search_pattern = f"%{search}%"
        q = q.where(
            or_(
                cast(Draw.draw_no, String).like(search_pattern),
                cast(Draw.draw_date, String).like(search_pattern)
            )
        )

    # Count total filtered records
    total = db.execute(
        select(func.count()).select_from(q.subquery())
    ).scalar()

    # Fetch paginated results
    draws = db.execute(
        q.order_by(Draw.draw_no.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    return {
        "total": total,
        "years": years,
        "data": [
            {
                "draw_id": d.draw_id,
                "draw_no": d.draw_no,
                "draw_date": d.draw_date.isoformat(),
                "numbers": d.numbers,
                "bonus_number": d.bonus_number,
            }
            for d in draws
        ],
    }


@router.get("/api/predictions")
def list_predictions(
    product_code: str = "MEGA_645",
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Danh sách predictions."""
    preds = db.execute(
        select(Prediction)
        .where(Prediction.product_code == product_code)
        .order_by(Prediction.generated_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    total = db.execute(
        select(func.count()).where(Prediction.product_code == product_code)
    ).scalar()

    return {
        "total": total,
        "data": [
            {
                "prediction_id": p.prediction_id,
                "model_id": p.model_id,
                "predicted_draw_no": p.predicted_draw_no,
                "predicted_draw_date": p.predicted_draw_date.isoformat() if p.predicted_draw_date else None,
                "top6": p.top6_json,
                "actual_top6": p.actual_top6_json,
                "hit_count": p.hit_count_main,
                "status": p.status,
                "generated_at": p.generated_at.isoformat(),
                "reconciled_at": p.reconciled_at.isoformat() if p.reconciled_at else None,
            }
            for p in preds
        ],
    }


@router.get("/api/metrics/leaderboard")
def leaderboard(product_code: str = "MEGA_645", db: Session = Depends(get_db)):
    """Model leaderboard theo holdout precision@6."""
    models = db.execute(
        select(Model)
        .where(Model.product_code == product_code)
        .order_by(Model.created_at.desc())
    ).scalars().all()

    board = []
    for m in models:
        board.append({
            "model_id": m.model_id,
            "model_name": m.model_name,
            "algorithm": m.algorithm,
            "status": m.status,
            "precision_at_6": (m.metrics_summary_json or {}).get("precision_at_6"),
            "log_loss": (m.metrics_summary_json or {}).get("log_loss"),
            "brier_score": (m.metrics_summary_json or {}).get("brier_score"),
            "created_at": m.created_at.isoformat(),
        })

    board.sort(key=lambda x: x["precision_at_6"] or 0, reverse=True)
    return board


@router.get("/api/metrics/live-trend")
def live_trend(
    product_code: str = "MEGA_645",
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
):
    """Xu hướng precision@6 live theo thời gian."""
    metrics = db.execute(
        select(Metric)
        .where(
            Metric.product_code == product_code,
            Metric.eval_scope == "live",
        )
        .order_by(Metric.created_at.desc())
        .limit(limit)
    ).scalars().all()

    return [
        {
            "metric_id": m.metric_id,
            "precision_at_6": m.precision_at_6,
            "created_at": m.created_at.isoformat(),
            "metric_json": m.metric_json,
        }
        for m in reversed(metrics)
    ]
