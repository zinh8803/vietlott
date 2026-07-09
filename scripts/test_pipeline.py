"""Test full pipeline: seed -> features -> train -> predict -> dashboard."""
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


errors = []

print("=" * 60)
print("STEP 1: Seed MEGA_645")
ok, r = post("/internal/crawler/sync-draws", {"product_code": "MEGA_645", "use_seed": True})
print("Result:", ok, r)
if not ok:
    errors.append(f"Seed FAILED: {r}")

print()
print("STEP 2: Build Features")
ok, r = post(
    "/internal/features/build",
    {"product_code": "MEGA_645", "window_size": 20, "feature_version": "v1"},
)
print("Result:", ok, r)
if not ok:
    errors.append(f"Build features FAILED: {r}")

print()
print("STEP 3: Train All Models (takes 1-3 minutes)")
ok, r = post(
    "/internal/train",
    {"product_code": "MEGA_645", "window_size": 20, "feature_version": "v1", "use_celery": False},
)
if ok:
    print("Train OK! Champion ID:", r.get("champion_model_id"))
    print(json.dumps(r, indent=2))
else:
    print("FAIL:", r)
    errors.append(f"Train FAILED: {r}")

print()
print("STEP 4: Predict Next")
ok, r = post(
    "/internal/predict/next",
    {"product_code": "MEGA_645", "request_type": "manual"},
)
if ok:
    print("Predict OK! Top6:", r.get("top6"))
else:
    print("FAIL:", r)
    errors.append(f"Predict FAILED: {r}")

print()
print("STEP 5: Dashboard Summary")
ok, r = get("/api/dashboard/summary")
if ok:
    mega = r.get("MEGA_645", {})
    champ = mega.get("champion") or {}
    pred = mega.get("latest_prediction") or {}
    print("Champion:", champ.get("algorithm"), "| Model:", champ.get("model_name"))
    print("Latest pred top6:", pred.get("top6"))
else:
    print("FAIL:", r)
    errors.append(f"Dashboard FAILED: {r}")

print()
print("STEP 6: Leaderboard")
ok, r = get("/api/metrics/leaderboard?product_code=MEGA_645")
if ok:
    for m in r[:5]:
        p6 = m.get("precision_at_6") or 0
        alg = m["algorithm"]
        mid = m["model_id"]
        st = m["status"]
        print(f"  #{mid} {alg:15s} p@6={p6:.4f}  status={st}")
else:
    print("FAIL:", r)
    errors.append(f"Leaderboard FAILED: {r}")

print()
if errors:
    print("ERRORS:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
else:
    print("ALL STEPS PASSED!")
