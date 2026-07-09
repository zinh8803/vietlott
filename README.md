# VietlotAI – Hệ thống AI dự đoán xổ số Vietlott

> **Lưu ý pháp lý**: Hệ thống này là nền tảng học tập, thí nghiệm và backtest.  
> Không phải cam kết thắng. Xổ số chỉ dành cho người đủ 18 tuổi.

## Stack

| Layer      | Technology |
|------------|-----------|
| Backend    | FastAPI + SQLAlchemy + MySQL |
| ML         | scikit-learn + LightGBM + XGBoost |
| Queue      | Celery + Redis |
| Frontend   | React + Vite + Recharts |

## Khởi động nhanh

### 1. Cài Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Cấu hình database

Chỉnh `DATABASE_URL` trong `.env`:
```
DATABASE_URL=mysql+pymysql://root:yourpassword@localhost:3306/vietlott_ml
```

Tạo database trong MySQL:
```sql
CREATE DATABASE vietlott_ml CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Khởi tạo DB + seed dữ liệu mẫu

```bash
python scripts/init_db.py
```

### 4. Chạy backend

```bash
python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 5. Chạy frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

### 6. (Optional) Chạy Celery worker

```bash
# Cần Redis chạy: redis-server
python -m celery -A app.workers.celery_app worker --loglevel=info
```

## Pipeline qua UI

1. Truy cập http://localhost:5173
2. Vào trang **Điều khiển**
3. Chọn sản phẩm (Mega 6/45 hoặc Power 6/55)
4. Chạy theo thứ tự:
   - **Seed Data** → tạo dữ liệu mẫu
   - **Build Features** → tính sliding-window features
   - **Train All** → train Baseline + LightGBM + XGBoost, chọn Champion
   - **Predict Next** → dự đoán kỳ kế tiếp
   - **Reconcile** → đối chiếu kết quả

## Cấu trúc thư mục

```
vietlot/
├── app/
│   ├── api/routes/main.py     # FastAPI endpoints
│   ├── core/config.py         # Settings
│   ├── crawlers/              # Web scraper
│   ├── db/                    # ORM models + database
│   ├── features/              # Sliding window features
│   ├── train/                 # ML training modules
│   ├── predict/               # Prediction generator
│   ├── reconcile/             # Result reconciliation
│   └── workers/               # Celery tasks
├── frontend/                  # React + Vite dashboard
├── scripts/init_db.py         # DB initialization
└── requirements.txt
```
