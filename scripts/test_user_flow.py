"""Automated test script to verify user registration, login, daily ticket limit enforcement, and admin quota unlocking."""
from __future__ import annotations

import urllib.request
import json
import sys
import random

BASE = "http://localhost:8000"

def post(path, data, timeout=30):
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

def patch(path, data, timeout=30):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=body, headers={"Content-Type": "application/json"}, method="PATCH"
    )
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return True, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return False, json.loads(e.read())
        except Exception:
            return False, {"error": str(e)}

def main():
    print("=" * 60)
    print("STARTING USER TICKET LIMIT & QUOTA SYSTEM TEST")
    print("=" * 60)

    # 1. Register a new user
    rand_id = random.randint(1000, 9999)
    username = f"user_{rand_id}"
    display_name = f"Test User {rand_id}"
    password = "password123"

    print(f"\n[Step 1] Registering user: {username}...")
    ok, res = post("/api/auth/register", {
        "username": username,
        "display_name": display_name,
        "password": password
    })
    print("Register result:", ok, res)
    if not ok:
        print("Registration failed")
        sys.exit(1)
        
    user = res["user"]
    user_id = user["user_id"]
    print(f"Registered user with ID: {user_id}, limit: {user['daily_ticket_limit']}")

    # 2. Login as the user
    print(f"\n[Step 2] Logging in as {username}...")
    ok, res = post("/api/auth/login", {
        "username": username,
        "password": password
    })
    print("Login result:", ok, res)
    if not ok:
        print("Login failed")
        sys.exit(1)

    # 3. Create tickets up to the daily limit (limit is 3 by default)
    limit = user["daily_ticket_limit"]
    print(f"\n[Step 3] Creating {limit} tickets to hit daily limit...")
    for i in range(limit):
        ok, res = post("/api/tickets", {
            "user_id": user_id,
            "product_code": "BINGO18",
            "random_sample": True
        })
        print(f"Ticket {i+1} result: {ok}, remaining: {res.get('user', {}).get('remaining_today') if ok else 'error'}")
        if not ok:
            print("Failed to create ticket within quota")
            sys.exit(1)

    # 4. Attempt to create the 4th ticket (should fail)
    print("\n[Step 4] Attempting to create ticket exceeding limit (should fail)...")
    ok, res = post("/api/tickets", {
        "user_id": user_id,
        "product_code": "BINGO18",
        "random_sample": True
    })
    print("Result (expected False):", ok, res)
    if ok:
        print("Test FAILED: ticket was successfully created exceeding quota limit!")
        sys.exit(1)
    
    if res.get("detail", {}).get("code") == "DAILY_LIMIT_EXCEEDED":
        print("Successfully blocked ticket creation with DAILY_LIMIT_EXCEEDED error! User is now locked.")
    else:
        print("Test FAILED: did not receive DAILY_LIMIT_EXCEEDED error code", res)
        sys.exit(1)

    # 5. Admin updates the user's limit (+5) and unlocks them
    print("\n[Step 5] Admin: increasing quota by 5 and unlocking user...")
    ok, res = patch(f"/api/admin/users/{user_id}/quota", {
        "add_quota": 5,
        "unlock": True
    })
    print("Admin update result:", ok, res)
    if not ok:
        print("Admin failed to update user quota")
        sys.exit(1)
        
    updated_user = res["user"]
    print(f"User is now: locked={updated_user['is_locked']}, limit={updated_user['daily_ticket_limit']}, remaining={updated_user['remaining_today']}")
    if updated_user["is_locked"] or updated_user["remaining_today"] != 5:
        print("Test FAILED: user state is incorrect after admin unlock")
        sys.exit(1)

    # 6. Verify user can now create another ticket successfully
    print("\n[Step 6] Creating ticket after admin quota unlock...")
    ok, res = post("/api/tickets", {
        "user_id": user_id,
        "product_code": "BINGO18",
        "random_sample": True
    })
    print("Ticket creation after unlock result:", ok, res)
    if not ok:
        print("Failed to create ticket after unlocking user quota")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("ALL USER QUOTA & LIMIT SYSTEM TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    main()
