"""Script khoi tao du lieu, crawl ky moi nhat, train va predict cho ca 2 san pham."""
from __future__ import annotations

import os
import sys
import urllib.request
import json

BASE = "http://localhost:8000"

def post(path, data, timeout=600):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return True, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return False, json.loads(e.read())
        except Exception:
            return False, {"error": str(e)}

def run_pipeline_for_product(product_code: str):
    print("=" * 60)
    print(f"RUNNING PIPELINE FOR: {product_code}")
    print("=" * 60)
    
    # Step 1: Seed du lieu lich su mau (150 draws de co du sample hoc)
    print("\n[Step 1] Seeding historical draws...")
    ok, res = post("/internal/crawler/sync-draws", {"product_code": product_code, "use_seed": True})
    print("Result:", ok, res)
    if not ok:
        print(f"FAILED to seed {product_code}")
        return
        
    # Step 2: Crawl du lieu moi nhat (thuc te tu vietlott.vn)
    print("\n[Step 2] Crawling latest live draw from vietlott.vn...")
    ok, res = post("/internal/crawler/sync-draws", {"product_code": product_code, "use_seed": False, "force": True})
    print("Result:", ok, res)
    if not ok:
        print(f"FAILED to crawl latest live draw for {product_code}")
        return
        
    # Step 3: Build features
    print("\n[Step 3] Building features...")
    ok, res = post("/internal/features/build", {"product_code": product_code, "window_size": 20, "feature_version": "v1"})
    print("Result:", ok, res)
    if not ok:
        print(f"FAILED to build features for {product_code}")
        return
        
    # Step 4: Train models
    print("\n[Step 4] Training all models (Dummy, LogReg, RandomForest, LightGBM, XGBoost)...")
    ok, res = post("/internal/train", {"product_code": product_code, "window_size": 20, "feature_version": "v1", "use_celery": False})
    if ok:
        print("Train OK! Champion model ID:", res.get("champion_model_id"))
        print(json.dumps(res, indent=2))
    else:
        print(f"FAILED to train models for {product_code}:", res)
        return
        
    # Step 5: Predict next draw
    print("\n[Step 5] Predicting next draw numbers...")
    ok, res = post("/internal/predict/next", {"product_code": product_code, "request_type": "manual"})
    if ok:
        print("Prediction SUCCESS!")
        print(f"  Predicted Draw No: #{res.get('predicted_draw_no')}")
        print(f"  Top 6 Predicted Numbers: {res.get('top6')}")
        print(f"  Generated at: {res.get('generated_at')}")
    else:
        print(f"FAILED to predict next draw for {product_code}:", res)

def main():
    # Chay pipeline cho ca MEGA_645 va POWER_655
    run_pipeline_for_product("MEGA_645")
    run_pipeline_for_product("POWER_655")
    
    # Kiem tra Dashboard summary cuoi cung
    print("\n" + "=" * 60)
    print("CHECKING DASHBOARD SUMMARY")
    print("=" * 60)
    try:
        r = urllib.request.urlopen(BASE + "/api/dashboard/summary", timeout=10)
        data = json.loads(r.read())
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Dashboard query failed: {e}")

if __name__ == "__main__":
    main()
