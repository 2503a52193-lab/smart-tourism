import json
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, User, Destination, Hotel, Booking
from flask_jwt_extended import create_access_token

client = app.test_client()

def test_hotel_maps_integration():
    print("==================================================")
    print("TESTING GOOGLE MAPS INTEGRATION FOR EVERY HOTEL")
    print("==================================================")

    with app.app_context():
        # 1. Fetch public hotels catalog
        res = client.get("/api/hotels")
        assert res.status_code == 200, f"Failed /api/hotels: {res.status_code}"
        hotels = res.get_json()
        print(f"Total active hotels verified in catalog: {len(hotels)}")
        assert len(hotels) > 0, "No hotels found in catalog"

        # Check multiple destinations
        destinations_covered = set()
        for h in hotels:
            assert "google_maps_url" in h, f"Missing google_maps_url in hotel: {h.get('name')}"
            assert h["google_maps_url"].startswith("https://www.google.com/maps"), f"Invalid google_maps_url: {h['google_maps_url']}"
            assert "address" in h, f"Missing address in hotel: {h.get('name')}"
            assert "latitude" in h, f"Missing latitude key in hotel: {h.get('name')}"
            assert "longitude" in h, f"Missing longitude key in hotel: {h.get('name')}"
            if h.get("destination"):
                destinations_covered.add(h["destination"].lower())

        print(f"Hotels span across destinations: {sorted(list(destinations_covered))}")
        assert len(destinations_covered) >= 3, "Expected hotels across at least 3 destinations"

        # Spot check several hotels in different destinations
        sample_hotels = hotels[:5]
        for h in sample_hotels:
            print(f"  * Hotel: {h['name']} ({h.get('destination', 'India')})")
            print(f"    - Address: {h['address']}")
            print(f"    - Google Maps URL: {h['google_maps_url']}")
            if h.get('latitude') and h.get('longitude'):
                print(f"    - Coordinates: ({h['latitude']}, {h['longitude']})")

        # 2. Test Admin Hotel Creation & Editing with Maps Fields
        admin = User.query.filter_by(role="admin").first()
        if not admin:
            admin = User(name="Test Admin", email="admin@roamly.com", role="admin")
            admin.set_password("admin-secret-password-123")
            db.session.add(admin)
            db.session.commit()
        admin_token = create_access_token(identity=str(admin.id), additional_claims={"role": "admin", "email": admin.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        first_dest = Destination.query.filter_by(active=True).first()
        assert first_dest is not None, "No active destination found"

        # Create new hotel via admin API
        new_hotel_payload = {
            "destination_id": first_dest.id,
            "name": "The Grand Azure Bay Resort",
            "nightly_rate": 5500,
            "rating": 4.8,
            "address": "Opposite Sunset Point, Calangute, Goa 403516",
            "google_maps_url": "https://www.google.com/maps/place/Calangute+Beach/@15.5432,73.7554,16z",
            "latitude": 15.5432,
            "longitude": 73.7554,
            "description": "Ultra luxury coastal resort with private cabanas.",
            "is_demo": True,
            "facilities": ["Pool", "WiFi", "Ocean View"],
        }
        create_res = client.post("/api/admin/hotels", json=new_hotel_payload, headers=admin_headers)
        assert create_res.status_code == 201, f"Admin create hotel failed: {create_res.status_code} - {create_res.get_data(as_text=True)}"
        created_hotel = create_res.get_json()["hotel"]
        hotel_id = created_hotel["id"]

        assert created_hotel["google_maps_url"] == new_hotel_payload["google_maps_url"]
        assert created_hotel["latitude"] == 15.5432
        assert created_hotel["longitude"] == 73.7554
        print(f"\nPASS: Admin created new hotel with verified map link & coordinates: ID #{hotel_id}")

        # Update hotel via admin API
        update_payload = {
            "address": "Updated Beachfront Promenade, Calangute, Goa 403516",
            "google_maps_url": "https://www.google.com/maps/place/Updated+Location/@15.5450,73.7580,16z",
            "latitude": 15.5450,
            "longitude": 73.7580,
        }
        update_res = client.put(f"/api/admin/hotels/{hotel_id}", json=update_payload, headers=admin_headers)
        assert update_res.status_code == 200, f"Admin update hotel failed: {update_res.status_code}"
        updated_hotel = update_res.get_json()["hotel"]
        assert updated_hotel["address"] == update_payload["address"]
        assert updated_hotel["google_maps_url"] == update_payload["google_maps_url"]
        assert updated_hotel["latitude"] == 15.5450
        assert updated_hotel["longitude"] == 73.7580
        print(f"PASS: Admin updated hotel address, Google Maps link, and coordinates successfully")

        # 3. Test Booking API returns Google Maps details
        customer = User.query.filter_by(role="customer").first()
        if not customer:
            customer = User(name="Test Customer", email="traveler@example.com", role="customer")
            customer.set_password("password-traveler-123")
            db.session.add(customer)
            db.session.commit()
        cust_token = create_access_token(identity=str(customer.id), additional_claims={"role": "customer", "email": customer.email})
        cust_headers = {"Authorization": f"Bearer {cust_token}"}

        # Add a room to the newly created hotel
        room_payload = {
            "name": "Deluxe Sea Facing Room",
            "nightly_rate": 5500,
            "capacity": 2,
            "available_rooms": 5,
            "price_basis": "estimate",
        }
        room_res = client.post(f"/api/admin/hotels/{hotel_id}/rooms", json=room_payload, headers=admin_headers)
        assert room_res.status_code == 201
        room_id = room_res.get_json()["room_type"]["id"]

        # Make a test booking on created_hotel
        from datetime import date, timedelta
        check_in = date.today() + timedelta(days=5)
        check_out = date.today() + timedelta(days=7)
        booking_payload = {
            "hotel_id": hotel_id,
            "destination_id": first_dest.id,
            "room_type_id": room_id,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": 2,
            "rooms": 1,
        }
        create_booking_res = client.post("/api/bookings", json=booking_payload, headers=cust_headers)
        assert create_booking_res.status_code == 201, f"Booking failed: {create_booking_res.status_code} - {create_booking_res.get_data(as_text=True)}"
        booking_data = create_booking_res.get_json()["booking"]
        assert booking_data["hotel_address"] == updated_hotel["address"]
        assert booking_data["hotel_google_maps_url"] == updated_hotel["google_maps_url"]
        assert booking_data["hotel_latitude"] == 15.5450
        assert booking_data["hotel_longitude"] == 73.7580
        print(f"PASS: Created booking #{booking_data['id']} returned hotel Google Maps URL & coordinates")

        book_res = client.get("/api/bookings", headers=cust_headers)
        assert book_res.status_code == 200, f"Failed /api/bookings: {book_res.status_code}"
        bookings = book_res.get_json()
        print(f"Customer has {len(bookings)} bookings in history")
        for b in bookings[:3]:
            assert "hotel_address" in b
            assert "hotel_google_maps_url" in b
            print(f"  * Booking #{b['id']}: {b['hotel']} | Map: {b['hotel_google_maps_url']}")

        # 4. Check Intercity Transport remains Buses & Trains Only (No taxis)
        transport_res = client.get("/api/transport/services")
        assert transport_res.status_code == 200
        services = transport_res.get_json()
        modes = {s["mode"] for s in services}
        print(f"\nIntercity transport modes available in catalog: {modes}")
        assert "taxi" not in modes, "Taxis must not be present in intercity transport catalog"
        assert modes.issubset({"bus", "train"}), "Intercity transport must only contain buses and trains"
        print("PASS: Intercity transport strictly restricted to buses and trains")

        print("\n==================================================")
        print("ALL GOOGLE MAPS INTEGRATION CHECKS PASSED 100%!")
        print("==================================================")

if __name__ == "__main__":
    test_hotel_maps_integration()
