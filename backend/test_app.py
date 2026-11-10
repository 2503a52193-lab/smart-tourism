import os
import unittest
from datetime import date, timedelta
from io import BytesIO

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-for-isolated-unit-tests-only"

from openpyxl import load_workbook
from werkzeug.security import generate_password_hash

from app import (
    Booking, Destination, Hotel, HotelProfile, RoomType, SavedItinerary,
    TouristAttraction, TransportReservation, TransportService, User, app, db,
)
from seed_data import (
    DESTINATIONS, clear_hotel_place_catalog, seed_verified_catalog,
)


class TourismApiTests(unittest.TestCase):
    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        self.customer = User(
            name="Asha Rao", email="asha@example.com",
            password_hash=generate_password_hash("customer-password-123"), role="customer",
        )
        self.other_customer = User(
            name="Dev Shah", email="dev@example.com",
            password_hash=generate_password_hash("another-password-123"), role="customer",
        )
        self.admin = User(
            name="Site Admin", email="admin@example.com",
            password_hash=generate_password_hash("administrator-password-123"), role="admin",
        )
        self.destination = Destination(name="Munnar", region="Kerala", description="Tea country")
        db.session.add_all([self.customer, self.other_customer, self.admin, self.destination])
        db.session.flush()
        self.hotel = Hotel(
            destination_id=self.destination.id, name="Hill View", nightly_rate=5000,
            price_basis="verified", source_url="https://hotel.example/property",
        )
        db.session.add(self.hotel)
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def login_token(self, email, password, role):
        response = self.client.post("/api/auth/login", json={
            "email": email, "password": password, "role": role,
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()["token"]

    def test_cors_allows_both_local_frontend_hostnames(self):
        for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
            with self.subTest(origin=origin):
                response = self.client.options(
                    "/api/auth/login",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "content-type",
                    },
                )
                self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), origin)

    def test_admin_can_sign_in_with_username(self):
        self.admin.name = "sriram"
        self.admin.password_hash = generate_password_hash("333")
        db.session.commit()

        response = self.client.post("/api/auth/login", json={
            "email": "sriram", "password": "333", "role": "admin",
        })

        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["user"]["role"], "admin")

    def test_roles_and_customer_booking_isolation(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        other_token = self.login_token("dev@example.com", "another-password-123", "customer")
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")

        denied = self.client.get("/api/admin/bookings", headers={"Authorization": f"Bearer {customer_token}"})
        self.assertEqual(denied.status_code, 403)
        denied_customer_api = self.client.get("/api/bookings", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(denied_customer_api.status_code, 403)

        check_in = date.today() + timedelta(days=10)
        payload = {
            "destination_id": self.destination.id, "hotel_id": self.hotel.id, "guests": 2,
            "check_in": check_in.isoformat(), "check_out": (check_in + timedelta(days=2)).isoformat(),
        }
        missing_room = self.client.post(
            "/api/bookings", headers={"Authorization": f"Bearer {customer_token}"}, json=payload
        )
        self.assertEqual(missing_room.status_code, 409)
        room = RoomType(
            hotel_id=self.hotel.id, name="Standard", nightly_rate=5000,
            capacity=2, available_rooms=2, price_basis="verified",
        )
        db.session.add(room)
        db.session.commit()
        payload["room_type_id"] = room.id
        created = self.client.post(
            "/api/bookings", headers={"Authorization": f"Bearer {customer_token}"}, json=payload
        )
        self.assertEqual(created.status_code, 201, created.get_json())
        self.assertEqual(created.get_json()["booking"]["amount"], 10000)

        own = self.client.get("/api/bookings", headers={"Authorization": f"Bearer {customer_token}"})
        other = self.client.get("/api/bookings", headers={"Authorization": f"Bearer {other_token}"})
        self.assertEqual(len(own.get_json()), 1)
        self.assertEqual(other.get_json(), [])

    def test_budget_assistant_recommends_live_hotels_per_person(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        response = self.client.post(
            "/api/assistant/recommendations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"budget_per_person": 6000, "nights": 2, "travelers": 2},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        result = response.get_json()
        self.assertEqual(result["message"], "Found 1 stay options within your per-person lodging budget.")
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["matches"][0]["hotel"], "Hill View")
        self.assertEqual(result["matches"][0]["estimated_total"], 10000)
        self.assertEqual(result["matches"][0]["estimated_per_person"], 5000)
        self.assertTrue(result["matches"][0]["within_budget"])
        self.assertTrue(result["lodging_only"])

        self.destination2 = Destination(name="Goa", region="Goa")
        db.session.add(self.destination2)
        db.session.flush()
        second_hotel = Hotel(destination_id=self.destination2.id, name="Beach House", nightly_rate=1000)
        db.session.add(second_hotel)
        db.session.commit()

        selected_destination = self.client.post(
            "/api/assistant/recommendations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "budget_per_person": 6000,
                "nights": 2,
                "travelers": 2,
                "destination_id": self.destination.id,
            },
        )
        self.assertEqual(selected_destination.status_code, 200, selected_destination.get_json())
        self.assertEqual(len(selected_destination.get_json()["matches"]), 1)
        self.assertEqual(selected_destination.get_json()["matches"][0]["destination"], "Munnar")

        invalid_destination = self.client.post(
            "/api/assistant/recommendations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"budget_per_person": 6000, "destination_id": 9999},
        )
        self.assertEqual(invalid_destination.status_code, 400)

        no_fit = self.client.post(
            "/api/assistant/recommendations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"budget_per_person": 1000, "nights": 2, "travelers": 1},
        )
        self.assertEqual(no_fit.status_code, 200, no_fit.get_json())
        self.assertEqual(no_fit.get_json()["matches"], [])
        self.assertTrue(no_fit.get_json()["alternatives"])
        self.assertFalse(no_fit.get_json()["alternatives"][0]["within_budget"])

        denied = self.client.post(
            "/api/assistant/recommendations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"budget_per_person": 6000},
        )
        self.assertEqual(denied.status_code, 403)
        invalid = self.client.post(
            "/api/assistant/recommendations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"budget_per_person": -1},
        )
        self.assertEqual(invalid.status_code, 400)

    def test_budget_assistant_uses_only_available_priced_rooms(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        room = RoomType(
            hotel_id=self.hotel.id, name="Deluxe", nightly_rate=2500, capacity=2,
            available_rooms=1, price_basis="estimate",
        )
        db.session.add(room)
        db.session.commit()
        headers = {"Authorization": f"Bearer {customer_token}"}
        response = self.client.post(
            "/api/assistant/recommendations",
            headers=headers,
            json={"budget_per_person": 3000, "nights": 2, "travelers": 2},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["matches"][0]["room_type"], "Deluxe")
        self.assertEqual(response.get_json()["matches"][0]["estimated_total"], 5000)

        room.available_rooms = 0
        db.session.commit()
        unavailable = self.client.post(
            "/api/assistant/recommendations",
            headers=headers,
            json={"budget_per_person": 3000, "nights": 2, "travelers": 2},
        )
        self.assertEqual(unavailable.status_code, 200, unavailable.get_json())
        self.assertEqual(unavailable.get_json()["matches"], [])

    def test_admin_filter_and_real_xlsx_export(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        room = RoomType(
            hotel_id=self.hotel.id, name="Standard", nightly_rate=5000,
            capacity=2, available_rooms=2, price_basis="verified",
        )
        db.session.add(room)
        db.session.commit()
        check_in = date.today() + timedelta(days=10)
        created = self.client.post("/api/bookings", headers={"Authorization": f"Bearer {customer_token}"}, json={
            "destination_id": self.destination.id, "hotel_id": self.hotel.id,
            "room_type_id": room.id, "guests": 2,
            "check_in": check_in.isoformat(), "check_out": (check_in + timedelta(days=2)).isoformat(),
        })
        self.assertEqual(created.status_code, 201)
        headers = {"Authorization": f"Bearer {admin_token}"}
        booking_id = created.get_json()["booking"]["id"]
        summary = self.client.get("/api/admin/summary", headers=headers)
        self.assertEqual(summary.status_code, 200, summary.get_json())
        self.assertEqual(summary.get_json()["revenue"], 0)
        self.assertEqual(len(summary.get_json()["monthly"]), 6)
        marked_paid = self.client.patch(
            f"/api/admin/bookings/{booking_id}", headers=headers, json={"payment_status": "paid"}
        )
        self.assertEqual(marked_paid.status_code, 200, marked_paid.get_json())
        paid_summary = self.client.get("/api/admin/summary", headers=headers)
        self.assertEqual(paid_summary.get_json()["revenue"], 10000)
        filtered = self.client.get("/api/admin/bookings?search=asha&status=pending", headers=headers)
        self.assertEqual(len(filtered.get_json()), 1)
        self.assertEqual(filtered.get_json()[0]["customer_email"], "asha@example.com")

        exported = self.client.get("/api/admin/bookings/export?search=asha", headers=headers)
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(
            exported.mimetype,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        sheet = load_workbook(BytesIO(exported.data), read_only=True).active
        self.assertEqual(sheet.max_row, 2)
        self.assertEqual(sheet.cell(1, 1).value, "Booking ID")
        self.assertEqual(sheet.cell(2, 2).value, "Asha Rao")
        self.assertEqual(sheet.cell(2, 9).value, 10000)

    def test_room_type_capacity_and_inventory_are_enforced(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        room = RoomType(
            hotel_id=self.hotel.id, name="Lake view", nightly_rate=7200,
            capacity=3, available_rooms=1, price_basis="verified",
        )
        db.session.add(room)
        db.session.commit()
        check_in = date.today() + timedelta(days=10)
        payload = {
            "destination_id": self.destination.id, "hotel_id": self.hotel.id,
            "room_type_id": room.id, "guests": 3,
            "check_in": check_in.isoformat(), "check_out": (check_in + timedelta(days=2)).isoformat(),
        }
        created = self.client.post(
            "/api/bookings", headers={"Authorization": f"Bearer {customer_token}"}, json=payload
        )
        self.assertEqual(created.status_code, 201, created.get_json())
        self.assertEqual(created.get_json()["booking"]["amount"], 14400)
        self.assertEqual(db.session.get(RoomType, room.id).available_rooms, 1)
        available = self.client.get(
            f"/api/hotels/{self.hotel.id}/availability",
            query_string={
                "room_type_id": room.id,
                "check_in": check_in.isoformat(),
                "check_out": (check_in + timedelta(days=2)).isoformat(),
            },
        )
        self.assertEqual(available.status_code, 200, available.get_json())
        self.assertEqual(available.get_json()["available_rooms"], 0)

        sold_out = self.client.post(
            "/api/bookings", headers={"Authorization": f"Bearer {customer_token}"}, json=payload
        )
        self.assertEqual(sold_out.status_code, 409)

    def test_admin_can_verify_an_existing_hotel_rate_before_booking(self):
        self.hotel.nightly_rate = 0
        self.hotel.price_basis = "unavailable"
        db.session.commit()
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        updated = self.client.put(
            f"/api/admin/hotels/{self.hotel.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "nightly_rate": 6400,
                "price_basis": "verified",
                "source_url": "https://hotel.example/rates",
            },
        )
        self.assertEqual(updated.status_code, 200, updated.get_json())
        self.assertEqual(updated.get_json()["hotel"]["price_basis"], "verified")
        room = RoomType(
            hotel_id=self.hotel.id, name="Quoted room", nightly_rate=6400,
            capacity=2, available_rooms=1, price_basis="verified",
        )
        db.session.add(room)
        db.session.commit()

        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        check_in = date.today() + timedelta(days=10)
        booking = self.client.post(
            "/api/bookings",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id,
                "hotel_id": self.hotel.id,
                "room_type_id": room.id,
                "guests": 2,
                "check_in": check_in.isoformat(),
                "check_out": (check_in + timedelta(days=2)).isoformat(),
            },
        )
        self.assertEqual(booking.status_code, 201, booking.get_json())
        self.assertEqual(booking.get_json()["booking"]["amount"], 12800)

    def test_admin_can_edit_destination_hotel_and_room_details(self):
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        headers = {"Authorization": f"Bearer {admin_token}"}

        updated_destination = self.client.put(
            f"/api/admin/destinations/{self.destination.id}",
            headers=headers,
            json={
                "name": "Munnar Valley",
                "region": "Kerala",
                "description": "Updated destination details",
                "image_url": "https://images.example/munnar.jpg",
            },
        )
        self.assertEqual(updated_destination.status_code, 200, updated_destination.get_json())
        self.assertEqual(updated_destination.get_json()["destination"]["name"], "Munnar Valley")

        updated_hotel = self.client.put(
            f"/api/admin/hotels/{self.hotel.id}",
            headers=headers,
            json={
                "name": "Hill View Resort",
                "destination_id": self.destination.id,
                "nightly_rate": 0,
                "price_basis": "unavailable",
                "source_url": "https://hotel.example/property",
                "address": "Tea Garden Road",
                "image_url": "https://images.example/hotel.jpg",
                "price_tier": "mid-range",
                "rating": 4.4,
                "facilities": ["Wi-Fi", "Restaurant"],
            },
        )
        self.assertEqual(updated_hotel.status_code, 200, updated_hotel.get_json())
        updated_hotel_data = updated_hotel.get_json()["hotel"]
        self.assertEqual(updated_hotel_data["name"], "Hill View Resort")
        self.assertEqual(updated_hotel_data["address"], "Tea Garden Road")
        self.assertEqual(updated_hotel_data["image_url"], "https://images.example/hotel.jpg")
        self.assertEqual(updated_hotel_data["price_tier"], "mid-range")
        self.assertEqual(updated_hotel_data["facilities"], ["Wi-Fi", "Restaurant"])

        added_room = self.client.post(
            f"/api/admin/hotels/{self.hotel.id}/rooms",
            headers=headers,
            json={
                "name": "Garden room",
                "nightly_rate": 0,
                "capacity": 3,
                "available_rooms": None,
                "price_basis": "unavailable",
            },
        )
        self.assertEqual(added_room.status_code, 201, added_room.get_json())
        room_id = added_room.get_json()["room_type"]["id"]
        edited_room = self.client.put(
            f"/api/admin/rooms/{room_id}",
            headers=headers,
            json={
                "name": "Deluxe garden room",
                "nightly_rate": 6200,
                "price_basis": "verified",
                "capacity": 3,
                "available_rooms": 5,
            },
        )
        self.assertEqual(edited_room.status_code, 200, edited_room.get_json())
        self.assertEqual(edited_room.get_json()["room_type"]["name"], "Deluxe garden room")
        self.assertEqual(edited_room.get_json()["room_type"]["nightly_rate"], 6200)

        archived_room = self.client.delete(f"/api/admin/rooms/{room_id}", headers=headers)
        self.assertEqual(archived_room.status_code, 200, archived_room.get_json())
        self.assertFalse(archived_room.get_json()["room_type"]["active"])
        admin_hotel = self.client.get("/api/admin/hotels", headers=headers).get_json()[0]
        self.assertFalse(admin_hotel["rooms"][0]["active"])
        restored_room = self.client.put(
            f"/api/admin/rooms/{room_id}", headers=headers, json={"active": True},
        )
        self.assertEqual(restored_room.status_code, 200, restored_room.get_json())
        self.assertTrue(restored_room.get_json()["room_type"]["active"])

    def test_customer_catalog_includes_bookable_demo_hotels(self):
        demo_hotel = Hotel(
            destination_id=self.destination.id,
            name="Invented demo property",
            nightly_rate=1000,
            price_basis="estimate",
            is_demo=True,
        )
        db.session.add(demo_hotel)
        db.session.flush()
        demo_room = RoomType(
            hotel_id=demo_hotel.id,
            name="Sample room",
            nightly_rate=1000,
            capacity=2,
            available_rooms=3,
            price_basis="estimate",
        )
        db.session.add(demo_room)
        db.session.commit()

        hotels = self.client.get("/api/hotels").get_json()
        self.assertEqual(
            [hotel["name"] for hotel in hotels],
            ["Hill View", "Invented demo property"],
        )
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        admin_hotels = self.client.get(
            "/api/admin/hotels", headers={"Authorization": f"Bearer {admin_token}"},
        ).get_json()
        self.assertEqual(
            [hotel["name"] for hotel in admin_hotels],
            ["Hill View", "Invented demo property"],
        )

        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        check_in = date.today() + timedelta(days=10)
        created_booking = self.client.post(
            "/api/bookings",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id,
                "hotel_id": demo_hotel.id,
                "room_type_id": demo_room.id,
                "check_in": check_in.isoformat(),
                "check_out": (check_in + timedelta(days=2)).isoformat(),
                "guests": 2,
            },
        )
        self.assertEqual(created_booking.status_code, 201, created_booking.get_json())
        self.assertTrue(created_booking.get_json()["booking"]["is_demo"])

        budget_result = self.client.post(
            "/api/assistant/recommendations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"budget_per_person": 6000, "nights": 2, "travelers": 2},
        )
        self.assertEqual(budget_result.status_code, 200, budget_result.get_json())
        demo_recommendation = next(
            item for item in budget_result.get_json()["matches"]
            if item["hotel"] == "Invented demo property"
        )
        self.assertTrue(demo_recommendation["is_demo"])

        start_date = date.today() + timedelta(days=30)
        trip_result = self.client.post(
            "/api/assistant/trip-recommendations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id,
                "origin": "Hyderabad",
                "start_date": start_date.isoformat(),
                "end_date": (start_date + timedelta(days=2)).isoformat(),
                "travelers": 2,
                "budget_per_person": 50000,
                "interests": [],
            },
        )
        self.assertEqual(trip_result.status_code, 200, trip_result.get_json())
        result = trip_result.get_json()
        self.assertNotIn(
            "Invented demo property",
            [item["hotel"] for item in result["accommodation_options"]],
        )
        self.assertNotIn(
            "Invented demo property",
            [item["hotel"] for item in result["unpriced_accommodations"]],
        )

    def test_catalog_cleanup_preserves_history_and_allows_admin_to_add_fresh_records(self):
        unbooked_hotel = Hotel(
            destination_id=self.destination.id,
            name="Old unbooked listing",
            nightly_rate=0,
            price_basis="unavailable",
        )
        booked_hotel = Hotel(
            destination_id=self.destination.id,
            name="Historical booking hotel",
            nightly_rate=5000,
            price_basis="verified",
            source_url="https://hotel.example/property",
        )
        db.session.add_all([unbooked_hotel, booked_hotel])
        db.session.flush()
        db.session.add_all([
            RoomType(
                hotel_id=unbooked_hotel.id,
                name="Old room",
                nightly_rate=1000,
                available_rooms=2,
            ),
            RoomType(
                hotel_id=booked_hotel.id,
                name="Historical room",
                nightly_rate=5000,
                available_rooms=2,
                total_rooms=2,
                price_basis="verified",
            ),
            TouristAttraction(
                destination_id=self.destination.id,
                name="Old place",
                category="Museum",
            ),
        ])
        historical_room = RoomType.query.filter_by(
            hotel_id=booked_hotel.id
        ).one()
        db.session.flush()
        historical_booking = Booking(
            user_id=self.customer.id,
            destination_id=self.destination.id,
            hotel_id=booked_hotel.id,
            room_type_id=historical_room.id,
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=32),
            guests=2,
            rooms_count=1,
            amount=10000,
        )
        db.session.add(historical_booking)
        db.session.commit()

        cleanup = clear_hotel_place_catalog(db)
        self.assertEqual(cleanup, {
            "hotels deleted": 2,
            "booked hotels archived": 1,
            "places deleted": 1,
        })
        self.assertIsNone(db.session.get(Hotel, unbooked_hotel.id))
        self.assertFalse(db.session.get(Hotel, booked_hotel.id).active)
        self.assertEqual(Booking.query.count(), 1)
        self.assertEqual(TouristAttraction.query.count(), 0)
        self.assertEqual(self.client.get("/api/hotels").get_json(), [])
        admin_token = self.login_token(
            "admin@example.com", "administrator-password-123", "admin"
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        self.assertEqual(
            self.client.get("/api/admin/hotels", headers=admin_headers).get_json(),
            [],
        )
        archived_catalog = self.client.get(
            "/api/admin/hotels?include_archived=true", headers=admin_headers
        ).get_json()
        self.assertEqual([hotel["name"] for hotel in archived_catalog], ["Historical booking hotel"])

        seed_verified_catalog(db)
        self.assertEqual(Hotel.query.count(), 1)
        self.assertEqual(TouristAttraction.query.count(), 0)

        invalid_rating_hotel = self.client.post(
            "/api/admin/hotels",
            headers=admin_headers,
            json={
                "name": "Invalid rating listing",
                "destination_id": self.destination.id,
                "nightly_rate": 2500,
                "rating": 6,
            },
        )
        self.assertEqual(invalid_rating_hotel.status_code, 400, invalid_rating_hotel.get_json())

        created_hotel = self.client.post(
            "/api/admin/hotels",
            headers=admin_headers,
            json={
                "name": "Fresh admin listing",
                "destination_id": self.destination.id,
                "nightly_rate": 2500,
                "rating": 4.3,
            },
        )
        self.assertEqual(created_hotel.status_code, 201, created_hotel.get_json())
        new_hotel_id = created_hotel.get_json()["hotel"]["id"]
        created_hotel_data = created_hotel.get_json()["hotel"]
        self.assertNotIn("check_in", created_hotel_data)
        self.assertNotIn("check_out", created_hotel_data)
        self.assertEqual(created_hotel_data["rating"], 4.3)
        self.assertEqual(
            [hotel["name"] for hotel in self.client.get(
                "/api/admin/hotels", headers=admin_headers
            ).get_json()],
            ["Fresh admin listing"],
        )
        added_room = self.client.post(
            f"/api/admin/hotels/{new_hotel_id}/rooms",
            headers=admin_headers,
            json={
                "name": "Admin-added room",
                "nightly_rate": 2500,
                "capacity": 2,
                "available_rooms": 3,
                "price_basis": "estimate",
            },
        )
        self.assertEqual(added_room.status_code, 201, added_room.get_json())
        created_place = self.client.post(
            "/api/admin/attractions",
            headers=admin_headers,
            json={
                "destination_id": self.destination.id,
                "name": "Fresh admin place",
                "category": "Museum",
            },
        )
        self.assertEqual(created_place.status_code, 201, created_place.get_json())
        self.assertEqual(TouristAttraction.query.count(), 1)

        customer_token = self.login_token(
            "asha@example.com", "customer-password-123", "customer"
        )
        booking_without_hotel_admin_dates = self.client.post(
            "/api/bookings",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id,
                "hotel_id": new_hotel_id,
                "room_type_id": added_room.get_json()["room_type"]["id"],
                "check_in": (date.today() + timedelta(days=2)).isoformat(),
                "check_out": (date.today() + timedelta(days=4)).isoformat(),
                "guests": 2,
            },
        )
        self.assertEqual(booking_without_hotel_admin_dates.status_code, 201, booking_without_hotel_admin_dates.get_json())
        check_in = date.today() + timedelta(days=10)
        fresh_booking = self.client.post(
            "/api/bookings",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id,
                "hotel_id": new_hotel_id,
                "room_type_id": added_room.get_json()["room_type"]["id"],
                "check_in": check_in.isoformat(),
                "check_out": (check_in + timedelta(days=2)).isoformat(),
                "guests": 2,
            },
        )
        self.assertEqual(fresh_booking.status_code, 201, fresh_booking.get_json())

    @unittest.skip("Automatic hotel/place seeding is intentionally disabled.")
    def test_bookable_demo_catalog_covers_every_hotel_and_destination(self):
        seed_verified_catalog(db)
        seeded = seed_demo_booking_data(db)
        self.assertEqual(
            seeded["demo room types added"],
            sum(map(len, HOTEL_LISTINGS.values())) * 2,
        )

        catalog = self.client.get("/api/hotels").get_json()
        source_names = {
            hotel_name
            for properties in HOTEL_LISTINGS.values()
            for hotel_name, _ in properties
        }
        source_hotels = [hotel for hotel in catalog if hotel["name"] in source_names]
        self.assertEqual(len(source_hotels), len(source_names))
        for hotel in source_hotels:
            with self.subTest(hotel=hotel["name"]):
                self.assertTrue(hotel["is_demo"])
                self.assertIn("Sample project address", hotel["address"])
                self.assertEqual(len(hotel["rooms"]), 2)
                self.assertTrue(all(room["nightly_rate"] > 0 for room in hotel["rooms"]))
                self.assertTrue(all(room["available_rooms"] > 0 for room in hotel["rooms"]))
                self.assertTrue(all(room["price_basis"] == "estimate" for room in hotel["rooms"]))

        customer_token = self.login_token(
            "asha@example.com", "customer-password-123", "customer"
        )
        customer_headers = {"Authorization": f"Bearer {customer_token}"}
        check_in = date.today() + timedelta(days=10)
        for destination_name, properties in HOTEL_LISTINGS.items():
            destination = Destination.query.filter_by(name=destination_name).one()
            hotel = Hotel.query.filter_by(
                destination_id=destination.id, name=properties[0][0]
            ).one()
            room = next(room for room in hotel.rooms if room.name == "Standard Room (demo)")
            response = self.client.post(
                "/api/bookings",
                headers=customer_headers,
                json={
                    "destination_id": destination.id,
                    "hotel_id": hotel.id,
                    "room_type_id": room.id,
                    "check_in": check_in.isoformat(),
                    "check_out": (check_in + timedelta(days=2)).isoformat(),
                    "guests": 2,
                },
            )
            self.assertEqual(response.status_code, 201, response.get_json())
            booking = response.get_json()["booking"]
            self.assertTrue(booking["is_demo"])
            self.assertTrue(booking["id"])
            self.assertEqual(booking["amount"], float(room.nightly_rate * 2))
        self.assertEqual(Booking.query.count(), len(HOTEL_LISTINGS))

        first_destination_name, first_properties = next(iter(HOTEL_LISTINGS.items()))
        first_destination = Destination.query.filter_by(name=first_destination_name).one()
        first_hotel = Hotel.query.filter_by(
            destination_id=first_destination.id, name=first_properties[0][0]
        ).one()
        first_room = next(
            room for room in first_hotel.rooms if room.name == "Standard Room (demo)"
        )
        check_availability = lambda start, end: self.client.get(
            f"/api/hotels/{first_hotel.id}/availability",
            query_string={
                "room_type_id": first_room.id,
                "check_in": start.isoformat(),
                "check_out": end.isoformat(),
            },
        )
        available = check_availability(check_in, check_in + timedelta(days=2))
        self.assertEqual(available.status_code, 200, available.get_json())
        self.assertEqual(available.get_json()["available_rooms"], 3)
        self.assertEqual(
            check_availability(check_in + timedelta(days=5), check_in + timedelta(days=7))
            .get_json()["available_rooms"],
            4,
        )

        invalid_dates = self.client.post(
            "/api/bookings",
            headers=customer_headers,
            json={
                "destination_id": first_destination.id,
                "hotel_id": first_hotel.id,
                "room_type_id": first_room.id,
                "check_in": check_in.isoformat(),
                "check_out": check_in.isoformat(),
                "guests": 2,
            },
        )
        self.assertEqual(invalid_dates.status_code, 400)
        over_capacity = self.client.post(
            "/api/bookings",
            headers=customer_headers,
            json={
                "destination_id": first_destination.id,
                "hotel_id": first_hotel.id,
                "room_type_id": first_room.id,
                "check_in": check_in.isoformat(),
                "check_out": (check_in + timedelta(days=2)).isoformat(),
                "guests": 3,
            },
        )
        self.assertEqual(over_capacity.status_code, 400)
        for _ in range(3):
            filled = self.client.post(
                "/api/bookings",
                headers=customer_headers,
                json={
                    "destination_id": first_destination.id,
                    "hotel_id": first_hotel.id,
                    "room_type_id": first_room.id,
                    "check_in": check_in.isoformat(),
                    "check_out": (check_in + timedelta(days=2)).isoformat(),
                    "guests": 2,
                },
            )
            self.assertEqual(filled.status_code, 201, filled.get_json())
        sold_out = self.client.post(
            "/api/bookings",
            headers=customer_headers,
            json={
                "destination_id": first_destination.id,
                "hotel_id": first_hotel.id,
                "room_type_id": first_room.id,
                "check_in": check_in.isoformat(),
                "check_out": (check_in + timedelta(days=2)).isoformat(),
                "guests": 2,
            },
        )
        self.assertEqual(sold_out.status_code, 409)

        admin_token = self.login_token(
            "admin@example.com", "administrator-password-123", "admin"
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        admin_bookings = self.client.get("/api/admin/bookings", headers=admin_headers)
        self.assertEqual(admin_bookings.status_code, 200, admin_bookings.get_json())
        self.assertEqual(len(admin_bookings.get_json()), len(HOTEL_LISTINGS) + 3)
        self.assertIn("customer_name", admin_bookings.get_json()[0])
        own_bookings = self.client.get("/api/bookings", headers=customer_headers)
        self.assertEqual(len(own_bookings.get_json()), len(HOTEL_LISTINGS) + 3)
        exported = self.client.get("/api/admin/bookings/export", headers=admin_headers)
        self.assertEqual(exported.status_code, 200)
        sheet = load_workbook(BytesIO(exported.data), read_only=True).active
        self.assertEqual(sheet.max_row, len(HOTEL_LISTINGS) + 4)

    def test_demo_hotel_booking_inventory_cancellation_and_ownership(self):
        demo_hotel = Hotel(
            destination_id=self.destination.id,
            name="Demo Munnar stay",
            nightly_rate=3500,
            price_basis="estimate",
            is_demo=True,
        )
        db.session.add(demo_hotel)
        db.session.flush()
        family_room = RoomType(
            hotel_id=demo_hotel.id,
            name="Family Room (demo)",
            nightly_rate=5600,
            capacity=4,
            available_rooms=2,
            total_rooms=2,
            price_basis="estimate",
        )
        db.session.add(family_room)
        db.session.commit()
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        other_token = self.login_token("dev@example.com", "another-password-123", "customer")
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        check_in = date.today() + timedelta(days=10)
        payload = {
            "destination_id": self.destination.id,
            "hotel_id": demo_hotel.id,
            "room_type_id": family_room.id,
            "check_in": check_in.isoformat(),
            "check_out": (check_in + timedelta(days=2)).isoformat(),
            "guests": 3,
            "rooms": 2,
        }

        invalid_dates = {**payload, "check_out": check_in.isoformat()}
        invalid = self.client.post(
            "/api/bookings", headers={"Authorization": f"Bearer {customer_token}"}, json=invalid_dates
        )
        self.assertEqual(invalid.status_code, 400)

        created = self.client.post(
            "/api/bookings", headers={"Authorization": f"Bearer {customer_token}"}, json=payload
        )
        self.assertEqual(created.status_code, 201, created.get_json())
        booking = created.get_json()["booking"]
        self.assertTrue(booking["is_demo"])
        self.assertEqual(booking["rooms"], 2)
        self.assertEqual(booking["amount"], float(family_room.nightly_rate * 4))
        self.assertEqual(db.session.get(RoomType, family_room.id).available_rooms, 2)
        self.assertEqual(self.client.get(
            "/api/bookings", headers={"Authorization": f"Bearer {customer_token}"}
        ).get_json()[0]["id"], booking["id"])

        confirmed = self.client.patch(
            f"/api/admin/bookings/{booking['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "confirmed"},
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.get_json())
        self.assertEqual(confirmed.get_json()["booking"]["status"], "confirmed")
        paid = self.client.patch(
            f"/api/admin/bookings/{booking['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"payment_status": "paid"},
        )
        self.assertEqual(paid.status_code, 200, paid.get_json())
        reopened = self.client.patch(
            f"/api/admin/bookings/{booking['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "pending"},
        )
        self.assertEqual(reopened.status_code, 200)

        forbidden = self.client.patch(
            f"/api/bookings/{booking['id']}",
            headers={"Authorization": f"Bearer {other_token}"},
            json={"status": "cancelled"},
        )
        self.assertEqual(forbidden.status_code, 404)
        cancelled = self.client.patch(
            f"/api/bookings/{booking['id']}",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"status": "cancelled"},
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.get_json())
        self.assertEqual(cancelled.get_json()["booking"]["status"], "cancelled")
        self.assertEqual(db.session.get(RoomType, family_room.id).available_rooms, 2)
        self.assertEqual(Hotel.query.filter_by(destination_id=self.destination.id, is_demo=True).count(), 1)

    def test_transport_route_reservations_and_customer_isolation(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        other_token = self.login_token("dev@example.com", "another-password-123", "customer")
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        service_date = date.today() + timedelta(days=5)
        bus = TransportService(
            mode="bus", origin="Hyderabad", destination="Goa", operator="Verified Bus",
            departure_time="20:00", arrival_time="08:00", service_date=service_date,
            ticket_price=1500, available_seats=4, availability_verified=True,
            price_basis="verified", source_url="https://operator.example/route",
        )
        taxi = TransportService(
            mode="train", origin="Hyderabad", destination="Goa", operator="Listed Train",
            departure_time="09:00", arrival_time="10:00", service_date=service_date,
            ticket_price=500, available_seats=None,
        )
        unverified_bus = TransportService(
            mode="bus", origin="Hyderabad", destination="Goa", operator="Unverified Bus",
            departure_time="21:00", arrival_time="09:00", service_date=service_date,
            ticket_price=900, available_seats=8,
        )
        db.session.add_all([bus, taxi, unverified_bus])
        db.session.commit()

        route = self.client.get(
            f"/api/transport/services?mode=bus&from=Hyderabad&to=Goa&date={service_date.isoformat()}"
        )
        self.assertEqual(
            {item["operator"] for item in route.get_json()},
            {"Verified Bus", "Unverified Bus"},
        )
        local = self.client.get("/api/transport/services?mode=train&from=Hyderabad&to=Goa")
        self.assertEqual([item["operator"] for item in local.get_json()], ["Listed Train"])

        request = self.client.post(
            "/api/transport/reservations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"service_id": bus.id, "seats": 2},
        )
        self.assertEqual(request.status_code, 201, request.get_json())
        reservation_id = request.get_json()["reservation"]["id"]
        self.assertEqual(request.get_json()["reservation"]["amount"], 3000)
        self.assertEqual(db.session.get(TransportService, bus.id).available_seats, 2)
        mine = self.client.get(
            "/api/transport/reservations", headers={"Authorization": f"Bearer {customer_token}"}
        )
        other = self.client.get(
            "/api/transport/reservations", headers={"Authorization": f"Bearer {other_token}"}
        )
        self.assertEqual(len(mine.get_json()), 1)
        self.assertEqual(other.get_json(), [])
        self.assertEqual(
            self.client.get("/api/admin/transport/reservations",
                            headers={"Authorization": f"Bearer {customer_token}"}).status_code,
            403,
        )
        admin_list = self.client.get(
            "/api/admin/transport/reservations",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(admin_list.get_json()[0]["customer_email"], "asha@example.com")

        cancelled = self.client.delete(
            f"/api/transport/reservations/{reservation_id}",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(db.session.get(TransportService, bus.id).available_seats, 4)
        self.assertEqual(db.session.get(TransportReservation, reservation_id).status, "cancelled")
        unverified_request = self.client.post(
            "/api/transport/reservations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"service_id": unverified_bus.id, "seats": 1},
        )
        self.assertEqual(unverified_request.status_code, 409)

    def test_admin_transport_crud_bus_train_taxi(self):
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Admin adds a Bus
        bus_resp = self.client.post(
            "/api/admin/transport/services",
            headers=admin_headers,
            json={
                "mode": "bus",
                "operator": "KSRTC Airavat",
                "service_name": "Club Class Multi-Axle",
                "service_type": "AC Sleeper (2+1)",
                "origin": "Bengaluru",
                "origin_station": "Kempegowda Bus Station",
                "destination": "Goa",
                "destination_station": "Panaji Kadamba Terminus",
                "departure_time": "21:00",
                "arrival_time": "07:30",
                "duration": "10h 30m",
                "distance_km": "560 km",
                "ticket_price": 1350,
                "available_seats": 32,
                "booking_url": "https://ksrtc.in",
                "price_basis": "verified",
                "availability_verified": True,
            },
        )
        self.assertEqual(bus_resp.status_code, 201, bus_resp.get_json())
        bus_id = bus_resp.get_json()["service"]["id"]
        self.assertEqual(bus_resp.get_json()["service"]["duration"], "10h 30m")

        # 2. Duplicate detection
        dup_resp = self.client.post(
            "/api/admin/transport/services",
            headers=admin_headers,
            json={
                "mode": "bus",
                "operator": "KSRTC Airavat",
                "service_name": "Club Class Multi-Axle",
                "service_type": "AC Sleeper (2+1)",
                "origin": "Bengaluru",
                "destination": "Goa",
                "departure_time": "21:00",
                "arrival_time": "07:30",
                "ticket_price": 1350,
            },
        )
        self.assertEqual(dup_resp.status_code, 409)

        # 3. Admin adds a Train
        train_resp = self.client.post(
            "/api/admin/transport/services",
            headers=admin_headers,
            json={
                "mode": "train",
                "operator": "Indian Railways / IRCTC",
                "service_name": "20608 - Vande Bharat Express",
                "service_type": "Vande Bharat Express",
                "origin": "Bengaluru",
                "origin_station": "KSR Bengaluru (SBC)",
                "destination": "Chennai",
                "destination_station": "MGR Chennai Central (MAS)",
                "departure_time": "14:50",
                "arrival_time": "19:20",
                "duration": "4h 30m",
                "distance_km": "360 km",
                "ticket_price": 995,
                "available_classes": "CC, EC",
                "class_fares": {"CC": 995, "EC": 1980},
                "booking_url": "https://www.irctc.co.in",
                "price_basis": "verified",
            },
        )
        self.assertEqual(train_resp.status_code, 201, train_resp.get_json())
        train_data = train_resp.get_json()["service"]
        self.assertEqual(train_data["available_classes"], "CC, EC")
        self.assertEqual(train_data["class_fares"]["EC"], 1980)
        train_id = train_data["id"]

        # 4. Admin tries to add a Taxi (Must be rejected, Taxi removed)
        taxi_resp = self.client.post(
            "/api/admin/transport/services",
            headers=admin_headers,
            json={
                "mode": "taxi",
                "operator": "Roamly Verified Chauffeur",
                "service_name": "Heritage Intercity Sedan",
                "service_type": "Sedan (Swift Dzire AC)",
                "origin": "Bengaluru",
                "destination": "Mysuru",
                "departure_time": "Flexible (24x7)",
                "arrival_time": "Est. 3h 15m travel",
                "ticket_price": 2750,
            },
        )
        self.assertEqual(taxi_resp.status_code, 400)
        self.assertIn("restricted to bus and train only", taxi_resp.get_json()["error"])

        # 5. Admin edits transport details
        edit_resp = self.client.put(
            f"/api/admin/transport/services/{train_id}",
            headers=admin_headers,
            json={"ticket_price": 1050, "duration": "4h 15m"},
        )
        self.assertEqual(edit_resp.status_code, 200)
        self.assertEqual(edit_resp.get_json()["service"]["ticket_price"], 1050)
        self.assertEqual(edit_resp.get_json()["service"]["duration"], "4h 15m")

        # 6. Admin archives and restores transport
        del_resp = self.client.delete(
            f"/api/admin/transport/services/{bus_id}",
            headers=admin_headers,
        )
        self.assertEqual(del_resp.status_code, 200)
        self.assertFalse(db.session.get(TransportService, bus_id).active)

        restore_resp = self.client.post(
            f"/api/admin/transport/services/{bus_id}/restore",
            headers=admin_headers,
        )
        self.assertEqual(restore_resp.status_code, 200)
        self.assertTrue(db.session.get(TransportService, bus_id).active)

        # 7. Customer searches transport with filters
        search_bus = self.client.get("/api/transport/services?mode=bus&from=Bengaluru&to=Goa")
        self.assertEqual(search_bus.status_code, 200)
        self.assertTrue(any(item["operator"] == "KSRTC Airavat" for item in search_bus.get_json()))

        search_train = self.client.get("/api/transport/services?mode=train&from=Bengaluru")
        self.assertEqual(search_train.status_code, 200)
        self.assertTrue(any("Vande Bharat" in item["service_name"] for item in search_train.get_json()))

        search_taxi = self.client.get("/api/transport/services?mode=taxi")
        self.assertEqual(search_taxi.status_code, 400)

    def test_itinerary_matches_interest_and_per_person_activity_budget(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        db.session.add_all([
            TouristAttraction(
                destination_id=self.destination.id, name="Tea Museum", category="Museum",
                interests=["history"], estimated_cost=300, duration_hours=2,
                cost_basis="verified",
            ),
            TouristAttraction(
                destination_id=self.destination.id, name="Tea Trail", category="Nature",
                interests=["nature"], estimated_cost=900, duration_hours=3,
                cost_basis="verified",
            ),
        ])
        db.session.commit()
        response = self.client.post(
            "/api/assistant/itinerary",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id, "days": 2,
                "budget_per_person": 500, "interests": ["history"],
            },
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        result = response.get_json()
        self.assertEqual(result["estimated_activity_cost"], 300)
        self.assertEqual(result["itinerary"][0]["places"][0]["name"], "Tea Museum")
        self.assertFalse(result["lodging_and_transport_included"])

    @unittest.skip("The legacy sourced property seed was removed; see admin-created catalog tests.")
    def test_real_catalog_refresh_is_repeatable_and_preserves_existing_records(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        initial_user_count = User.query.count()
        initial_hotel_count = Hotel.query.count()
        legacy_hotel = Hotel(
            destination_id=self.destination.id, name="DEMO ONLY - Legacy sample",
            nightly_rate=1234, is_demo=True, price_basis="estimate",
        )
        sample_hotel = Hotel(
            destination_id=self.destination.id, name="Roamly Demo Stay - Munnar",
            nightly_rate=3500, is_demo=True, price_basis="estimate",
        )
        legacy_transport = TransportService(
            destination_id=self.destination.id, mode="bus", origin="Sample",
            destination="Sample", operator="DEMO ONLY", service_name="DEMO ONLY",
            departure_time="Not verified", arrival_time="Not verified",
            service_date=date.today() + timedelta(days=5), ticket_price=600,
            is_demo=True, price_basis="estimate",
        )
        db.session.add_all([legacy_hotel, sample_hotel, legacy_transport])
        db.session.flush()
        db.session.add(RoomType(
            hotel_id=legacy_hotel.id, name="Legacy sample room", nightly_rate=1200,
        ))
        sample_room = RoomType(
            hotel_id=sample_hotel.id, name="Sample double",
            nightly_rate=3500, available_rooms=4, price_basis="estimate",
        )
        db.session.add(sample_room)
        db.session.add(HotelProfile(
            hotel_id=sample_hotel.id, rating=4.5, facilities=["sample"],
        ))
        db.session.flush()
        historical_booking = Booking(
            user_id=self.customer.id,
            destination_id=self.destination.id,
            hotel_id=sample_hotel.id,
            room_type_id=sample_room.id,
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=32),
            guests=2,
            rooms_count=1,
            amount=7000,
            status="pending",
            is_demo=True,
        )
        db.session.add(historical_booking)
        db.session.commit()
        denied = self.client.post(
            "/api/admin/catalog/seed-demo-data",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        self.assertEqual(denied.status_code, 403)
        first = seed_verified_catalog(db)
        second = seed_verified_catalog(db)
        self.assertEqual(first, {
            "destinations added": len(DESTINATIONS) - 1,
            "legacy destinations archived": 0,
            "real properties added": sum(len(properties) for properties in HOTEL_LISTINGS.values()),
            "sample properties archived": 2,
            "unverified properties archived": 0,
            "published rates cleared": 0,
            "sample rooms archived": 2,
            "attractions added": sum(len(items) for items in ATTRACTIONS.values()),
            "sample transport archived": 1,
            "unverified transport archived": 0,
        })
        self.assertTrue(all(count == 0 for count in second.values()))
        api_repeat = self.client.post(
            "/api/admin/catalog/seed-demo-data",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(api_repeat.status_code, 200, api_repeat.get_json())
        self.assertEqual(api_repeat.get_json()["updated"]["demo room types added"], 166)
        api_repeat_again = self.client.post(
            "/api/admin/catalog/seed-demo-data",
            headers={"Authorization": f"Bearer " + admin_token},
        )
        self.assertTrue(all(
            count == 0 for count in api_repeat_again.get_json()["updated"].values()
        ))
        self.assertEqual(User.query.count(), initial_user_count)
        self.assertEqual(
            Hotel.query.count(),
            initial_hotel_count + 2 + first["real properties added"],
        )
        for name, _region, _description in DESTINATIONS:
            destination = Destination.query.filter_by(name=name).first()
            self.assertIsNotNone(destination, name)
            self.assertTrue(destination.active)
            property_names = [hotel_name for hotel_name, _ in HOTEL_LISTINGS.get(name, [])]
            self.assertEqual(
                Hotel.query.filter(
                    Hotel.destination_id == destination.id, Hotel.active.is_(True),
                    Hotel.name.in_(property_names),
                ).count(),
                len(property_names),
            )
            places = TouristAttraction.query.filter_by(destination_id=destination.id, active=True).all()
            self.assertEqual(len(places), len(ATTRACTIONS[name]))
            self.assertTrue(all(not place.is_demo and place.cost_basis == "unverified" for place in places))
            self.assertTrue(all(place.estimated_cost == 0 for place in places))
        archived_demo_hotels = Hotel.query.filter(
            Hotel.is_demo.is_(True), Hotel.active.is_(False)
        ).all()
        self.assertEqual(len(archived_demo_hotels), 2)
        self.assertTrue(all(not hotel.active for hotel in archived_demo_hotels))
        self.assertTrue(all(hotel.nightly_rate == 0 for hotel in archived_demo_hotels))
        self.assertTrue(all(
            not room.active and room.nightly_rate == 0 and room.available_rooms is None
            for hotel in archived_demo_hotels for room in hotel.rooms
        ))
        self.assertIsNotNone(sample_hotel.profile)
        self.assertEqual(Booking.query.count(), 1)
        self.assertEqual(Booking.query.one().id, historical_booking.id)
        sample_service = TransportService.query.filter_by(is_demo=True, mode="bus").first()
        self.assertIsNone(sample_service.available_seats)
        self.assertIsNotNone(sample_service.destination_id)
        self.assertFalse(sample_service.active)
        real_hotel = Hotel.query.filter_by(name="Taj Ganges", active=True).one()
        self.assertEqual(real_hotel.price_basis, "estimate")
        self.assertTrue(real_hotel.source_url.startswith("https://"))
        self.assertEqual(len(real_hotel.rooms), 2)

        customer_headers = {"Authorization": f"Bearer {customer_token}"}
        sample_room = next(
            room for room in real_hotel.rooms if room.name == "Standard Room (demo)"
        )
        bookable = self.client.post(
            "/api/bookings",
            headers=customer_headers,
            json={
                "destination_id": real_hotel.destination_id,
                "hotel_id": real_hotel.id,
                "room_type_id": sample_room.id,
                "guests": 1,
                "check_in": (date.today() + timedelta(days=30)).isoformat(),
                "check_out": (date.today() + timedelta(days=32)).isoformat(),
            },
        )
        self.assertEqual(bookable.status_code, 201, bookable.get_json())
        prohibited_transport = self.client.post(
            "/api/transport/reservations",
            headers=customer_headers,
            json={"service_id": sample_service.id, "seats": 1},
        )
        self.assertEqual(prohibited_transport.status_code, 409)

    def test_trip_recommendations_include_only_route_and_date_matches(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        seed_verified_catalog(db)
        destination = Destination.query.filter_by(name="Goa").first()
        start_date = date.today() + timedelta(days=30)
        response = self.client.post(
            "/api/assistant/trip-recommendations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": destination.id,
                "origin": "Hyderabad",
                "start_date": start_date.isoformat(),
                "end_date": (start_date + timedelta(days=2)).isoformat(),
                "travelers": 2,
                "budget_per_person": 50000,
                "interests": ["beaches"],
            },
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        result = response.get_json()
        self.assertEqual(result["nights"], 2)
        self.assertEqual(result["accommodation_options"], [])
        self.assertEqual(result["unpriced_accommodations"], [])
        self.assertEqual(result["transport_options"], [])
        self.assertEqual(result["attractions"], [])
        self.assertIn("rather than guessed", result["pricing_notice"])
        no_route = self.client.post(
            "/api/assistant/trip-recommendations",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": destination.id,
                "origin": "Remote test town",
                "start_date": start_date.isoformat(),
                "end_date": (start_date + timedelta(days=2)).isoformat(),
                "travelers": 2,
                "budget_per_person": 50000,
                "interests": ["beaches"],
            },
        )
        self.assertEqual(no_route.status_code, 200)
        self.assertFalse(no_route.get_json()["transport_estimate_available"])
        self.assertTrue(all(
            not option["estimate_complete"]
            for option in no_route.get_json()["accommodation_options"]
        ))

    def test_generate_itinerary_with_selected_destination(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        # Add 3 attractions to Munnar
        db.session.add_all([
            TouristAttraction(
                destination_id=self.destination.id, name="Tea Gardens Viewpoint",
                category="Nature", duration_hours=2.5, entry_fee=50, estimated_cost=50,
                active=True,
            ),
            TouristAttraction(
                destination_id=self.destination.id, name="Attukad Waterfalls",
                category="Nature", duration_hours=2.0, entry_fee=0, estimated_cost=0,
                active=True,
            ),
            TouristAttraction(
                destination_id=self.destination.id, name="Munnar Spice Market",
                category="Culture", duration_hours=1.5, entry_fee=0, estimated_cost=0,
                active=True,
            ),
        ])
        db.session.commit()

        response = self.client.post(
            "/api/itineraries/generate",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id,
                "days": 2,
                "travelers": 2,
                "budget_per_person": 15000,
            },
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(data["destination"]["name"], "Munnar")
        self.assertEqual(data["days"], 2)
        self.assertEqual(data["travelers"], 2)
        self.assertEqual(len(data["daily_schedule"]), 2)
        self.assertTrue(data["within_budget"])
        self.assertGreater(data["estimated_accommodation"], 0)
        self.assertGreater(data["estimated_transport"], 0)
        self.assertGreater(data["estimated_food"], 0)
        self.assertEqual(data["total_estimated_cost"],
                         data["estimated_accommodation"] + data["estimated_transport"] +
                         data["estimated_food"] + data["estimated_sightseeing"])
        self.assertEqual(data["cost_per_person"], round(data["total_estimated_cost"] / 2, 2))
        self.assertEqual(data["remaining_budget"], round(30000 - data["total_estimated_cost"], 2))
        self.assertEqual(data["generation_mode"], "rule_based")
        self.assertIn("Database-Driven Smart Engine", data["generation_label"])

    def test_generate_itinerary_with_origin_includes_transport_recommendations(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        # Add transport services to Munnar
        db.session.add_all([
            TransportService(
                mode="bus", operator="KSRTC Express", origin="Kochi", destination="Munnar",
                departure_time="07:00", arrival_time="11:30", duration="4h 30m",
                service_date=date.today(), ticket_price=320, active=True, is_daily=True,
            ),
            TransportService(
                mode="train", operator="Indian Railways / IRCTC", origin="Kochi", destination="Munnar",
                service_name="DEMO-16315 - Kochuveli Express (Demo)",
                departure_time="06:30", arrival_time="09:45", duration="3h 15m",
                service_date=date.today(), ticket_price=210, active=True, is_daily=True,
            ),
        ])
        db.session.commit()

        response = self.client.post(
            "/api/itineraries/generate",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id,
                "origin": "Kochi",
                "days": 3,
                "travelers": 2,
                "budget_per_person": 18000,
            },
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertIn("recommended_transport", data)
        rec = data["recommended_transport"]
        self.assertEqual(rec["origin"], "Kochi")
        self.assertTrue(rec["has_route_matches"])
        self.assertGreater(len(rec["buses"]), 0)
        self.assertGreater(len(rec["trains"]), 0)
        self.assertNotIn("taxis", rec)
        self.assertIsNotNone(rec.get("recommended_bus"))
        self.assertIsNotNone(rec.get("recommended_train"))
        self.assertGreater(data["estimated_transport"], 0)
        self.assertEqual(
            data["total_estimated_cost"],
            data["estimated_accommodation"] + data["estimated_transport"] +
            data["estimated_food"] + data["estimated_sightseeing"]
        )

    def test_generate_itinerary_without_destination_recommends_destinations(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        # Add another destination
        kochi = Destination(name="Kochi", state="Kerala", region="South India", description="Historic port city")
        db.session.add(kochi)
        db.session.commit()

        response = self.client.post(
            "/api/itineraries/generate",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": None,
                "days": 3,
                "travelers": 2,
                "budget_per_person": 20000,
            },
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertIsNotNone(data["destination"])
        self.assertGreater(len(data["recommended_destinations"]), 0)
        self.assertTrue(any(d["name"] in ("Munnar", "Kochi") for d in data["recommended_destinations"]))

    def test_itinerary_insufficient_budget_explains_and_suggests_alternatives(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        response = self.client.post(
            "/api/itineraries/generate",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id,
                "days": 5,
                "travelers": 2,
                "budget_per_person": 1000,  # Very low budget for 5 days
            },
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertFalse(data["within_budget"])
        self.assertEqual(data["budget_status"], "insufficient_budget")
        self.assertIn("short by", data["budget_explanation"])
        self.assertGreater(len(data["alternatives"]), 0)
        alternative_types = [alt["type"] for alt in data["alternatives"]]
        self.assertIn("duration", alternative_types)

    def test_save_view_update_and_delete_itinerary_with_user_isolation(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        other_token = self.login_token("dev@example.com", "another-password-123", "customer")

        # Save an itinerary for Asha
        payload = {
            "destination_id": self.destination.id,
            "title": "Munnar 3-Day Tea Explorer",
            "days": 3,
            "travelers": 2,
            "budget_per_person": 12000,
            "total_budget": 24000,
            "estimated_accommodation": 7500,
            "estimated_transport": 2700,
            "estimated_food": 4500,
            "estimated_sightseeing": 600,
            "total_estimated_cost": 15300,
            "cost_per_person": 7650,
            "remaining_budget": 8700,
            "within_budget": True,
            "itinerary_data": [{"day": 1, "schedule": []}],
            "generation_mode": "rule_based",
        }
        create_res = self.client.post(
            "/api/itineraries",
            headers={"Authorization": f"Bearer {customer_token}"},
            json=payload,
        )
        self.assertEqual(create_res.status_code, 201, create_res.get_json())
        itinerary_id = create_res.get_json()["itinerary"]["id"]
        self.assertEqual(create_res.get_json()["itinerary"]["title"], "Munnar 3-Day Tea Explorer")

        # Asha can see her saved itinerary
        asha_list = self.client.get(
            "/api/itineraries",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        self.assertEqual(asha_list.status_code, 200)
        self.assertEqual(len(asha_list.get_json()), 1)
        self.assertEqual(asha_list.get_json()[0]["id"], itinerary_id)

        # Dev cannot see Asha's saved itinerary (user isolation)
        dev_list = self.client.get(
            "/api/itineraries",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        self.assertEqual(dev_list.status_code, 200)
        self.assertEqual(len(dev_list.get_json()), 0)

        dev_detail = self.client.get(
            f"/api/itineraries/{itinerary_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        self.assertEqual(dev_detail.status_code, 404)

        # Asha can update title
        update_res = self.client.put(
            f"/api/itineraries/{itinerary_id}",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"title": "Updated Munnar Adventure"},
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.get_json()["itinerary"]["title"], "Updated Munnar Adventure")

        # Asha can delete the saved itinerary
        delete_res = self.client.delete(
            f"/api/itineraries/{itinerary_id}",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        self.assertEqual(delete_res.status_code, 200)
        self.assertEqual(SavedItinerary.query.count(), 0)

    def test_hotel_booking_reference_generation_and_address_persistence(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        hotel = Hotel(
            destination_id=self.destination.id,
            name="Hillview Palace",
            address="123 Tea Garden Road, Munnar, Kerala 685612",
            nightly_rate=3500,
            price_basis="estimate",
            is_demo=True,
            check_in_policy="14:00",
            check_out_policy="11:00",
        )
        db.session.add(hotel)
        db.session.flush()
        room = RoomType(
            hotel_id=hotel.id,
            name="Deluxe Garden Room",
            nightly_rate=3500,
            capacity=2,
            total_rooms=5,
            available_rooms=5,
            price_basis="estimate",
        )
        db.session.add(room)
        db.session.commit()

        check_in = (date.today() + timedelta(days=10)).isoformat()
        check_out = (date.today() + timedelta(days=12)).isoformat()
        res = self.client.post(
            "/api/bookings",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id,
                "hotel_id": hotel.id,
                "room_type_id": room.id,
                "check_in": check_in,
                "check_out": check_out,
                "guests": 2,
                "rooms": 1,
            },
        )
        self.assertEqual(res.status_code, 201, res.get_json())
        data = res.get_json()["booking"]
        self.assertTrue(data["booking_reference"].startswith("BK-"))
        self.assertEqual(data["hotel_address"], "123 Tea Garden Road, Munnar, Kerala 685612")
        self.assertEqual(data["amount"], 7000.0)

    def test_admin_booking_search_by_reference_and_destination(self):
        customer_token = self.login_token("asha@example.com", "customer-password-123", "customer")
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        hotel = Hotel(
            destination_id=self.destination.id,
            name="Heritage Resort",
            address="Cliff Side, Munnar",
            nightly_rate=4000,
            price_basis="estimate",
            is_demo=True,
        )
        db.session.add(hotel)
        db.session.flush()
        room = RoomType(
            hotel_id=hotel.id,
            name="Standard Valley Room",
            nightly_rate=4000,
            capacity=2,
            total_rooms=4,
            available_rooms=4,
            price_basis="estimate",
        )
        db.session.add(room)
        db.session.commit()

        check_in = (date.today() + timedelta(days=15)).isoformat()
        check_out = (date.today() + timedelta(days=17)).isoformat()
        booking_res = self.client.post(
            "/api/bookings",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "destination_id": self.destination.id,
                "hotel_id": hotel.id,
                "room_type_id": room.id,
                "check_in": check_in,
                "check_out": check_out,
                "guests": 2,
                "rooms": 1,
            },
        )
        self.assertEqual(booking_res.status_code, 201)
        ref = booking_res.get_json()["booking"]["booking_reference"]

        # Search by booking reference
        admin_res = self.client.get(
            f"/api/admin/bookings?search={ref}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(admin_res.status_code, 200)
        items = admin_res.get_json()
        self.assertGreaterEqual(len(items), 1)
        self.assertEqual(items[0]["booking_reference"], ref)

        # Search by destination name
        admin_dest_res = self.client.get(
            f"/api/admin/bookings?search=Munnar",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(admin_dest_res.status_code, 200)
        self.assertGreaterEqual(len(admin_dest_res.get_json()), 1)

    def test_admin_hotel_crud_with_address_and_policies(self):
        admin_token = self.login_token("admin@example.com", "administrator-password-123", "admin")
        create_res = self.client.post(
            "/api/admin/hotels",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "destination_id": self.destination.id,
                "name": "Luxury Cloud Resort",
                "nightly_rate": 6500,
                "rating": 4.8,
                "address": "Hilltop Viewpoint Road, Munnar",
                "description": "Panoramic mountain views and organic tea plantation tours.",
                "check_in_policy": "15:00",
                "check_out_policy": "10:30",
                "facilities": ["WiFi", "Spa", "Pool"],
                "is_demo": True,
                "price_basis": "estimate",
            },
        )
        self.assertEqual(create_res.status_code, 201, create_res.get_json())
        hotel_data = create_res.get_json()["hotel"]
        hotel_id = hotel_data["id"]
        self.assertEqual(hotel_data["address"], "Hilltop Viewpoint Road, Munnar")
        self.assertEqual(hotel_data["check_in_policy"], "15:00")
        self.assertEqual(hotel_data["check_out_policy"], "10:30")

        # Edit hotel
        edit_res = self.client.put(
            f"/api/admin/hotels/{hotel_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Luxury Cloud Resort & Spa",
                "address": "Updated Hilltop Viewpoint Road, Munnar",
                "check_in_policy": "14:00",
            },
        )
        self.assertEqual(edit_res.status_code, 200, edit_res.get_json())
        updated_data = edit_res.get_json()["hotel"]
        self.assertEqual(updated_data["name"], "Luxury Cloud Resort & Spa")
        self.assertEqual(updated_data["address"], "Updated Hilltop Viewpoint Road, Munnar")
        self.assertEqual(updated_data["check_in_policy"], "14:00")


if __name__ == "__main__":
    unittest.main()

