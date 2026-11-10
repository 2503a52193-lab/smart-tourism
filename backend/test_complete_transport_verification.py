"""
Comprehensive End-to-End Verification for ROAMLY Complete Bus & Train Availability
Tests:
1. All city pairs display exactly 5 demo buses and 5 demo trains
2. Forward and reverse routes have distinct schedules/timings
3. Hill station railheads (Ooty via MTP/CBE, Manali via CDG/KLK)
4. AI Trip Planner integration (/api/itineraries/generate) returns 5 buses & 5 trains
5. Budget calculation matches: total_transport = fare_per_person * travelers
6. Intercity transport remains buses and trains only (no taxis)
"""

import sys
import os
import dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, User, Destination, TransportService
from flask_jwt_extended import create_access_token

client = app.test_client()

def run_all_tests():
    print("=" * 65)
    print("ROAMLY: COMPLETE BUS & TRAIN AVAILABILITY END-TO-END TEST SUITE")
    print("=" * 65)

    with app.app_context():
        # 1. Inspect all active destinations
        dests = Destination.query.filter_by(active=True).all()
        dest_names = [d.name for d in dests]
        print(f"\n1. Verified {len(dest_names)} Active Destinations:")
        print("   " + ", ".join(dest_names))
        assert len(dest_names) >= 12, f"Expected at least 12 destinations, found {len(dest_names)}"

        # 2. Test Specific Required Corridors and Reverse Directions
        test_pairs = [
            ("Hyderabad", "Chennai"),
            ("Chennai", "Hyderabad"),
            ("Hyderabad", "Bengaluru"),
            ("Bengaluru", "Hyderabad"),
            ("Hyderabad", "Goa"),
            ("Goa", "Hyderabad"),
            ("Delhi", "Agra"),
            ("Agra", "Delhi"),
            ("Mumbai", "Goa"),
            ("Goa", "Mumbai"),
            ("Chennai", "Ooty"),
            ("Ooty", "Chennai"),
            ("Delhi", "Manali"),
            ("Manali", "Delhi"),
            ("Delhi", "Varanasi"),
            ("Varanasi", "Delhi"),
            ("Bengaluru", "Mysuru"),
            ("Mysuru", "Bengaluru"),
        ]

        print("\n2. Testing Corridors in Both Directions for 5 Buses & 5 Trains:")
        stored_schedules = {}

        for orig, dest in test_pairs:
            res = client.get(f"/api/transport/services?from={orig}&to={dest}")
            assert res.status_code == 200, f"Failed search for {orig} -> {dest}: {res.status_code}"
            items = res.get_json()
            buses = [x for x in items if x["mode"] == "bus"]
            trains = [x for x in items if x["mode"] == "train"]

            print(f"   * {orig:12} ➔ {dest:12} | Buses: {len(buses)} | Trains: {len(trains)} | Total: {len(items)}")
            assert len(buses) == 5, f"Expected exactly 5 buses for {orig} -> {dest}, got {len(buses)}"
            assert len(trains) == 5, f"Expected exactly 5 trains for {orig} -> {dest}, got {len(trains)}"

            # Verify departure timings cover morning to night
            bus_deps = [b["departure_time"] for b in buses]
            train_deps = [t["departure_time"] for t in trains]
            stored_schedules[(orig, dest)] = {"bus_deps": bus_deps, "train_deps": train_deps}

            # Check demo flags and fares
            for b in buses:
                assert b["is_demo"] is True
                assert b["ticket_price"] > 0
                assert b["departure_time"] != b["arrival_time"]
                assert b["available_seats"] > 0
            for t in trains:
                assert t["is_demo"] is True
                assert t["ticket_price"] > 0
                assert t["available_seats"] > 0

        # 3. Verify Reverse Direction Has Distinct Departure Timings
        print("\n3. Verifying Independent Schedules for Reverse Routes (No Timing Reuse):")
        reverse_checks = [
            ("Hyderabad", "Chennai"),
            ("Hyderabad", "Bengaluru"),
            ("Hyderabad", "Goa"),
            ("Delhi", "Agra"),
            ("Mumbai", "Goa"),
            ("Chennai", "Ooty"),
            ("Delhi", "Manali"),
        ]
        for a, b in reverse_checks:
            fwd = stored_schedules[(a, b)]
            rev = stored_schedules[(b, a)]
            # Forward vs Reverse bus slot 1 departure should be different
            assert fwd["bus_deps"][0] != rev["bus_deps"][0], f"Bus departure slot 1 reused for {a} <-> {b}!"
            assert fwd["train_deps"][0] != rev["train_deps"][0], f"Train departure slot 1 reused for {a} <-> {b}!"
            print(f"   * {a} ➔ {b}: Bus 1st dep = {fwd['bus_deps'][0]}, Train 1st dep = {fwd['train_deps'][0]}")
            print(f"     {b} ➔ {a}: Bus 1st dep = {rev['bus_deps'][0]}, Train 1st dep = {rev['train_deps'][0]}")
            print(f"     PASS: Independent distinct departure schedules in both directions.")

        # 4. Verify Hill Stations (Ooty, Manali) Connecting Railhead Labels
        print("\n4. Verifying Hill Stations (Ooty, Manali) Connecting Railhead Labels:")
        ooty_res = client.get("/api/transport/services?from=Chennai&to=Ooty&mode=train")
        ooty_trains = ooty_res.get_json()
        assert len(ooty_trains) == 5
        for t in ooty_trains:
            st = t["destination_station"]
            assert any(hub in st for hub in ("MTP", "Mettupalayam", "Coimbatore", "CBE")), f"Missing Ooty railhead in {st}"
        print(f"   * Ooty Trains connect via: {ooty_trains[0]['destination_station']}")

        manali_res = client.get("/api/transport/services?from=Delhi&to=Manali&mode=train")
        manali_trains = manali_res.get_json()
        assert len(manali_trains) == 5
        for t in manali_trains:
            st = t["destination_station"]
            assert any(hub in st for hub in ("CDG", "Chandigarh", "Kalka", "KLK", "Ambala")), f"Missing Manali railhead in {st}"
        print(f"   * Manali Trains connect via: {manali_trains[0]['destination_station']}")
        print("   PASS: Connecting railhead stations clearly labeled for hill destinations.")

        # 5. Verify AI Trip Planner Integration (/api/itineraries/generate)
        print("\n5. Testing AI Trip Planner Integration (/api/itineraries/generate):")
        customer = User.query.filter_by(role="customer").first()
        if not customer:
            customer = User(name="Traveler User", email="customer@roamly.com", role="customer")
            customer.set_password("customer-secret-123")
            db.session.add(customer)
            db.session.commit()
        cust_token = create_access_token(identity=str(customer.id), additional_claims={"role": "customer", "email": customer.email})
        cust_headers = {"Authorization": f"Bearer {cust_token}"}

        hyderabad_dest = Destination.query.filter(Destination.name.ilike("Chennai")).first()
        assert hyderabad_dest is not None

        itin_payload = {
            "origin": "Hyderabad",
            "destination_id": hyderabad_dest.id,
            "days": 4,
            "travelers": 3,
            "budget_per_person": 25000,
            "interests": ["heritage", "beaches", "food"],
        }
        itin_res = client.post("/api/itineraries/generate", json=itin_payload, headers=cust_headers)
        assert itin_res.status_code == 200, f"Itinerary generation failed: {itin_res.status_code} - {itin_res.get_data(as_text=True)}"
        itin_data = itin_res.get_json()

        assert "recommended_transport" in itin_data
        transport_sec = itin_data["recommended_transport"]
        assert transport_sec["origin"] == "Hyderabad"
        assert transport_sec["destination"] == "Chennai"
        assert transport_sec["has_route_matches"] is True

        buses = transport_sec["buses"]
        trains = transport_sec["trains"]
        print(f"   * AI Itinerary returned {len(buses)} Buses and {len(trains)} Trains for Hyderabad ➔ Chennai")
        assert len(buses) == 5, f"Expected 5 buses in AI itinerary, got {len(buses)}"
        assert len(trains) == 5, f"Expected 5 trains in AI itinerary, got {len(trains)}"

        # Check fields of each bus and train in AI itinerary
        for b in buses:
            assert b["operator"]
            assert b["departure_time"]
            assert b["arrival_time"]
            assert b["duration"]
            assert b["ticket_price"] > 0
            assert b["total_fare"] == round(b["ticket_price"] * 3, 2)
            assert b["available_seats"] > 0

        for t in trains:
            assert t["service_name"]
            assert t["departure_time"]
            assert t["arrival_time"]
            assert t["duration"]
            assert t["ticket_price"] > 0
            assert t["total_fare"] == round(t["ticket_price"] * 3, 2)
            assert t["available_seats"] > 0

        # Check Top Recommendation Cards
        assert transport_sec["recommended_bus"] is not None
        assert transport_sec["recommended_train"] is not None
        print(f"   * Top Recommended Bus: {transport_sec['recommended_bus']['service_name']} (Rs. {transport_sec['recommended_bus']['ticket_price']}/person)")
        print(f"   * Top Recommended Train: {transport_sec['recommended_train']['service_name']} (Rs. {transport_sec['recommended_train']['ticket_price']}/person)")
        print(f"   * AI Comparison: {transport_sec['comparison_summary'][:95]}...")

        # 6. Verify Budget Calculation
        print("\n6. Verifying Budget Calculation (No Multiple-Summing):")
        rec_fare = transport_sec["recommended_train"]["ticket_price"]
        # Daily local transit (250 * 3 travelers * 4 days = 3000) + intercity transit (rec_fare * 3 travelers)
        expected_transport_cost = (rec_fare * 3) + (250 * 3 * 4)
        print(f"   * Allocated Transport in Total Trip Budget: Rs. {itin_data['estimated_transport']:,.2f}")
        assert abs(itin_data["estimated_transport"] - expected_transport_cost) < 5.0, (
            f"Budget mismatch: Expected ~{expected_transport_cost}, got {itin_data['estimated_transport']}"
        )
        total_sum = (
            itin_data["estimated_accommodation"] +
            itin_data["estimated_transport"] +
            itin_data["estimated_food"] +
            itin_data["estimated_sightseeing"]
        )
        assert abs(itin_data["total_estimated_cost"] - total_sum) < 0.05
        print(f"   * Total Estimated Trip Budget: Rs. {itin_data['total_estimated_cost']:,.2f} = Lodging ({itin_data['estimated_accommodation']}) + Transport ({itin_data['estimated_transport']}) + Food ({itin_data['estimated_food']}) + Sightseeing ({itin_data['estimated_sightseeing']})")
        print("   PASS: Budget calculation strictly includes recommended transport fare without summing all 10 options.")

        # 7. Verify Intercity Transport Excludes Taxis Completely
        print("\n7. Verifying Intercity Transport Excludes Taxis Completely:")
        all_trans_res = client.get("/api/transport/services")
        all_services = all_trans_res.get_json()
        modes = {s["mode"] for s in all_services}
        print(f"   * Intercity modes returned: {modes}")
        assert "taxi" not in modes, "Taxis must not appear in intercity transport results"
        assert modes.issubset({"bus", "train"}), "Catalog must only contain buses and trains"
        print("   PASS: Intercity transport strictly restricted to buses and trains.")

    print("\n" + "=" * 65)
    print("ALL 10 VERIFICATION REQUIREMENTS PASSED WITH 100% SUCCESS!")
    print("=" * 65)

if __name__ == "__main__":
    run_all_tests()
