"""Script kiem tra end-to-end pipeline cho BINGO18."""
from __future__ import annotations

import urllib.request
import json
import sys

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

def get(path):
    try:
        r = urllib.request.urlopen(BASE + path, timeout=30)
        return True, json.loads(r.read())
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 60)
    print("STARTING BINGO18 INTEGRATION TEST")
    print("=" * 60)
    
    # 1. Seed
    print("\n[Step 1] Seeding BINGO18 data...")
    ok, res = post("/internal/crawler/sync-draws", {"product_code": "BINGO18", "use_seed": True})
    print("Seeding result:", ok, res)
    if not ok:
        print("Test FAILED at Step 1")
        sys.exit(1)
        
    # 2. Build features
    print("\n[Step 2] Building features for BINGO18...")
    ok, res = post("/internal/features/build", {"product_code": "BINGO18", "window_size": 10, "feature_version": "v1"})
    print("Build features result:", ok, res)
    if not ok:
        print("Test FAILED at Step 2")
        sys.exit(1)
        
    # 3. Train models
    print("\n[Step 3] Training models for BINGO18...")
    ok, res = post("/internal/train", {"product_code": "BINGO18", "window_size": 10, "feature_version": "v1", "use_celery": False})
    print("Train result:", ok, res)
    if not ok:
        print("Test FAILED at Step 3")
        sys.exit(1)
        
    # 4. Predict
    print("\n[Step 4] Generating next prediction for BINGO18...")
    ok, res = post("/internal/predict/next", {"product_code": "BINGO18", "request_type": "manual"})
    print("Predict result:", ok, res)
    if not ok:
        print("Test FAILED at Step 4")
        sys.exit(1)
        
    # 5. Dashboard summary check
    print("\n[Step 5] Checking Dashboard Summary API...")
    ok, res = get("/api/dashboard/summary")
    if ok:
        print("Dashboard summary for BINGO18:")
        print(json.dumps(res.get("BINGO18"), indent=2))
    else:
        print("Dashboard summary failed:", res)
        sys.exit(1)
        
    print("\n" + "=" * 60)
    print("ALL BINGO18 PIPELINE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    main()
