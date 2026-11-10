import sys
import json
from datetime import date, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from app import app

client = app.test_client()

_token = None

def get_auth_token():
    global _token
    if _token:
        return _token
    # Try demo login
    resp = client.post("/api/auth/login", json={
        "email": "asha@example.com",
        "password": "customer-password-123",
        "role": "customer"
    })
    data = resp.get_json() or {}
    if "token" in data:
        _token = data["token"]
        return _token
    # Or admin login
    resp2 = client.post("/api/auth/login", json={
        "email": "sriram",
        "password": "333",
        "role": "admin"
    })
    data2 = resp2.get_json() or {}
    _token = data2.get("token")
    return _token

def api_get(endpoint, params=None):
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = client.get(f"/api{endpoint}", query_string=params or {}, headers=headers)
    return json.loads(resp.data.decode("utf-8"))

def api_post(endpoint, body):
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = client.post(f"/api{endpoint}", json=body, headers=headers)
    return json.loads(resp.data.decode("utf-8"))

def test_daily_availability():
    print("\n--- TEST 1: Daily Availability Across Multiple Dates (Hyderabad -> Chennai) ---")
    today = date.today()
    date1 = (today + timedelta(days=1)).isoformat()
    date2 = (today + timedelta(days=2)).isoformat()
    date3 = (today + timedelta(days=30)).isoformat()

    res1 = api_get("/transport/services", {"from": "Hyderabad", "to": "Chennai", "date": date1})
    res2 = api_get("/transport/services", {"from": "Hyderabad", "to": "Chennai", "date": date2})
    res3 = api_get("/transport/services", {"from": "Hyderabad", "to": "Chennai", "date": date3})

    buses1 = [s for s in res1 if s.get("mode") == "bus"]
    trains1 = [s for s in res1 if s.get("mode") == "train"]

    buses2 = [s for s in res2 if s.get("mode") == "bus"]
    trains2 = [s for s in res2 if s.get("mode") == "train"]

    buses3 = [s for s in res3 if s.get("mode") == "bus"]
    trains3 = [s for s in res3 if s.get("mode") == "train"]

    print(f"Date {date1}: {len(buses1)} buses, {len(trains1)} trains (total: {len(res1)})")
    print(f"Date {date2}: {len(buses2)} buses, {len(trains2)} trains (total: {len(res2)})")
    print(f"Date {date3}: {len(buses3)} buses, {len(trains3)} trains (total: {len(res3)})")

    assert len(buses1) == 5, f"Expected 5 buses, got {len(buses1)}"
    assert len(trains1) == 5, f"Expected 5 trains, got {len(trains1)}"
    assert len(buses2) == 5, f"Expected 5 buses on date 2, got {len(buses2)}"
    assert len(trains2) == 5, f"Expected 5 trains on date 2, got {len(trains2)}"
    assert len(buses3) == 5, f"Expected 5 buses on date 3, got {len(buses3)}"
    assert len(trains3) == 5, f"Expected 5 trains on date 3, got {len(trains3)}"

    # Check identical IDs and pricing
    ids1 = [s["id"] for s in res1]
    ids2 = [s["id"] for s in res2]
    ids3 = [s["id"] for s in res3]
    assert ids1 == ids2 == ids3, "Service IDs must be identical across all dates!"
    print("[PASS] Daily availability verified across 3 distinct dates!")

def test_reverse_routes():
    print("\n--- TEST 2: Bidirectional Reverse Routes ---")
    pairs = [
        ("Hyderabad", "Chennai"),
        ("Chennai", "Hyderabad"),
        ("Hyderabad", "Bengaluru"),
        ("Bengaluru", "Hyderabad"),
        ("Delhi", "Agra"),
        ("Agra", "Delhi"),
        ("Mumbai", "Goa"),
        ("Goa", "Mumbai"),
        ("Chennai", "Ooty"),
        ("Ooty", "Chennai"),
        ("Delhi", "Manali"),
        ("Manali", "Delhi")
    ]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    for orig, dest in pairs:
        res = api_get("/transport/services", {"from": orig, "to": dest, "date": tomorrow})
        buses = [s for s in res if s.get("mode") == "bus"]
        trains = [s for s in res if s.get("mode") == "train"]
        print(f"  {orig} -> {dest}: {len(buses)} buses, {len(trains)} trains")
        assert len(buses) == 5, f"Expected 5 buses for {orig} -> {dest}, got {len(buses)}"
        assert len(trains) == 5, f"Expected 5 trains for {orig} -> {dest}, got {len(trains)}"
    print("[PASS] Reverse routes and bidirectional symmetry verified!")

def test_itinerary_and_hotels_preservation():
    print("\n--- TEST 3: Preservation of Complete AI Itinerary and Hotels Only ---")
    # Test Itinerary generation
    itin_payload = {
        "budget_per_person": 15000,
        "travelers": 2,
        "days": 3,
        "origin": "Hyderabad",
        "destination_id": None
    }
    itin_res = api_post("/itineraries/generate", itin_payload)
    if "destination" not in itin_res:
        print("DEBUG ITIN RES:", itin_res)
    assert itin_res.get("destination") is not None, "Itinerary generation failed!"
    print(f"  Generated Itinerary for: {itin_res['destination']['name']}, Days: {itin_res['days']}")
    assert "recommended_transport" in itin_res, "Transport recommendations missing in Itinerary!"
    assert itin_res["recommended_transport"].get("recommended_bus") is not None, "Recommended bus missing!"
    assert itin_res["recommended_transport"].get("recommended_train") is not None, "Recommended train missing!"
    print("  Recommended Bus in Itinerary:", itin_res["recommended_transport"]["recommended_bus"]["operator"])
    print("  Recommended Train in Itinerary:", itin_res["recommended_transport"]["recommended_train"]["operator"])

    # Test Hotels Only recommendation
    hotels_payload = {
        "budget_per_person": 10000,
        "travelers": 2,
        "nights": 3,
        "destination_id": None
    }
    hotels_res = api_post("/assistant/recommendations", hotels_payload)
    matches = hotels_res.get("matches", []) or hotels_res.get("alternatives", [])
    print(f"  Hotels Only returned {len(matches)} hotel options")
    assert len(matches) > 0, "Hotels recommendation returned 0 matches!"

    print("[PASS] Existing AI Itinerary & Hotels Only modes preserved and functioning perfectly!")

def run_all():
    print("==================================================================")
    print("ROAMLY - TRANSPORT ONLY MODE COMPREHENSIVE VERIFICATION")
    print("==================================================================")
    test_daily_availability()
    test_reverse_routes()
    test_itinerary_and_hotels_preservation()
    print("\n==================================================================")
    print("ALL VERIFICATION SUITES PASSED (100% SUCCESS)")
    print("==================================================================")

if __name__ == "__main__":
    run_all()
