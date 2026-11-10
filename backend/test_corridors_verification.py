import json
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, User, Destination
from flask_jwt_extended import create_access_token

client = app.test_client()

CORRIDORS = [
    ("Hyderabad", "Goa"),
    ("Hyderabad", "Chennai"),
    ("Bengaluru", "Mysuru"),
    ("Delhi", "Agra"),
    ("Mumbai", "Goa"),
    ("Chennai", "Ooty"),
]

def test_all():
    print("========================================")
    print("VERIFYING TRANSPORT CORRIDORS & AI ASST")
    print("========================================")

    with app.app_context():
        # 1. Mode=taxi must be rejected with 400
        res = client.get("/api/transport/services?mode=taxi")
        assert res.status_code == 400, f"Expected 400 for mode=taxi, got {res.status_code}"
        print("PASS: mode=taxi is strictly rejected with 400 Bad Request")

        # Get or create customer for auth
        user = User.query.filter_by(role="customer").first()
        if not user:
            user = User(name="Test Customer", email="test@example.com", role="customer")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
        token = create_access_token(identity=str(user.id), additional_claims={"role": "customer", "email": user.email})
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Cache destination map
        dest_map = {}
        for d in Destination.query.filter_by(active=True).all():
            dest_map[d.name.lower()] = d
        print(f"Loaded destinations: {list(dest_map.keys())}")

        travelers = 3

        for origin, dest_name in CORRIDORS:
            print(f"\n--- Testing Corridor: {origin} -> {dest_name} (Travelers: {travelers}) ---")

            # 1. Search Buses
            res_bus = client.get(f"/api/transport/services?origin={origin}&destination={dest_name}&mode=bus")
            assert res_bus.status_code == 200, f"Failed bus search: {res_bus.status_code}"
            buses = res_bus.get_json()
            print(f"  [BUS] Found {len(buses)} bus services")
            assert len(buses) > 0, f"No buses found for {origin} -> {dest_name}"
            for b in buses[:2]:
                print(f"    * Bus: {b['operator']} ({b['service_name']}) | Fare/p: Rs.{b['ticket_price']} | Total ({travelers}): Rs.{b['ticket_price'] * travelers} | Type: {b['service_type']} | Status: {b['booking_status']}")
                assert b['mode'] == 'bus'

            # 2. Search Trains
            res_train = client.get(f"/api/transport/services?origin={origin}&destination={dest_name}&mode=train")
            assert res_train.status_code == 200, f"Failed train search: {res_train.status_code}"
            trains = res_train.get_json()
            print(f"  [TRAIN] Found {len(trains)} train services")
            assert len(trains) > 0, f"No trains found for {origin} -> {dest_name}"
            for t in trains[:2]:
                print(f"    * Train: {t['operator']} ({t['service_name']}) | Fare/p: Rs.{t['ticket_price']} | Total ({travelers}): Rs.{t['ticket_price'] * travelers} | Class: {t['available_classes']} | Status: {t['booking_status']}")
                assert t['mode'] == 'train'

            # 3. AI Itinerary Assistant Generation
            dest_obj = dest_map.get(dest_name.lower())
            dest_id = dest_obj.id if dest_obj else None

            itin_payload = {
                "origin": origin,
                "destination_id": dest_id,
                "budget_per_person": 12000,
                "travelers": travelers,
                "days": 3,
                "interests": ["Sightseeing", "Culture"]
            }
            res_itin = client.post("/api/itineraries/generate", json=itin_payload, headers=auth_headers)
            assert res_itin.status_code == 200, f"Itinerary generation failed: {res_itin.status_code} - {res_itin.get_data(as_text=True)}"
            res = res_itin.get_json()
            t_opts = res.get("transport_options", {})
            assert t_opts, "No transport_options in itinerary response"
            assert not t_opts.get("requires_origin"), "requires_origin should be false when origin is supplied"

            rec_bus = t_opts.get("recommended_bus")
            rec_train = t_opts.get("recommended_train")
            matched_services = t_opts.get("matched_services", [])

            print(f"  [AI ASSISTANT]")
            print(f"    * AI Analysis: {t_opts.get('recommendation_summary')}")
            assert rec_bus is not None, f"Expected recommended_bus for {origin}->{dest_name}"
            assert rec_train is not None, f"Expected recommended_train for {origin}->{dest_name}"

            print(f"    * Rec Bus: {rec_bus['operator']} | Rs.{rec_bus['estimated_fare_per_person']}/person | Total ({travelers}): Rs.{rec_bus['total_estimated_fare']}")
            assert rec_bus['total_estimated_fare'] == rec_bus['estimated_fare_per_person'] * travelers

            print(f"    * Rec Train: {rec_train['operator']} ({rec_train['service_name']}) | Rs.{rec_train['estimated_fare_per_person']}/person | Total ({travelers}): Rs.{rec_train['total_estimated_fare']}")
            assert rec_train['total_estimated_fare'] == rec_train['estimated_fare_per_person'] * travelers

            # Ensure NO taxis anywhere
            for s in matched_services:
                assert s['mode'] in ('bus', 'train'), f"Forbidden mode found: {s['mode']}"
            assert 'taxi' not in t_opts

            # Verify estimated transport in budget
            estimated_transport = res.get("estimated_transport", 0)
            total_estimated_cost = res.get("total_estimated_cost", 0)
            print(f"    * Estimated Transport budget: Rs.{estimated_transport} | Total trip cost: Rs.{total_estimated_cost}")
            assert estimated_transport > 0, "Transport expense should be factored into trip budget"

        # Test Missing Origin handling in AI Assistant
        print("\n--- Testing Missing Origin in AI Assistant ---")
        goa_obj = dest_map.get("goa")
        missing_origin_payload = {
            "origin": "",
            "destination_id": goa_obj.id if goa_obj else 1,
            "budget_per_person": 10000,
            "travelers": 2,
            "days": 4,
            "interests": ["Beaches"]
        }
        res_no_origin = client.post("/api/itineraries/generate", json=missing_origin_payload, headers=auth_headers)
        assert res_no_origin.status_code == 200
        t_opts_no_origin = res_no_origin.get_json().get("transport_options", {})
        assert t_opts_no_origin.get("requires_origin") == True, "Should flag requires_origin: True"
        print(f"  [PASS] Missing origin handled gracefully: {t_opts_no_origin.get('message')}")

        print("\n========================================")
        print("ALL 6 CORRIDORS & CRITERIA VERIFIED 100%!")
        print("========================================")

if __name__ == "__main__":
    test_all()
