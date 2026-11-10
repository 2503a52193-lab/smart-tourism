from __future__ import annotations

import math
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from io import BytesIO
from urllib.parse import urlsplit, urlunsplit

import click
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, jwt_required
from flask_sqlalchemy import SQLAlchemy
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import JSON, String, cast, func, or_, update
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import BadRequest

load_dotenv()

db = SQLAlchemy()
jwt = JWTManager()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Destination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, index=True)
    state = db.Column(db.String(120), nullable=False, default="")
    region = db.Column(db.String(160), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    image_url = db.Column(db.Text, nullable=False, default="")
    best_time_to_visit = db.Column(db.String(160), nullable=False, default="")
    budget_range = db.Column(db.String(100), nullable=False, default="")
    active = db.Column(db.Boolean, nullable=False, default=True)
    attractions = db.relationship("TouristAttraction", back_populates="destination", cascade="all, delete-orphan")


class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    destination_id = db.Column(db.Integer, db.ForeignKey("destination.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    nightly_rate = db.Column(db.Numeric(12, 2), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    price_tier = db.Column(db.String(20), nullable=False, default="unclassified")
    price_basis = db.Column(db.String(20), nullable=False, default="unverified")
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    source_url = db.Column(db.Text, nullable=False, default="")
    address = db.Column(db.Text, nullable=False, default="")
    google_maps_url = db.Column(db.Text, nullable=False, default="")
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    image_url = db.Column(db.Text, nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    check_in_policy = db.Column(db.String(160), nullable=False, default="14:00")
    check_out_policy = db.Column(db.String(160), nullable=False, default="11:00")
    destination = db.relationship("Destination")
    profile = db.relationship("HotelProfile", back_populates="hotel", uselist=False, cascade="all, delete-orphan")
    rooms = db.relationship("RoomType", back_populates="hotel", cascade="all, delete-orphan")


class HotelProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotel.id"), unique=True, nullable=False)
    rating = db.Column(db.Float)
    rating_verified = db.Column(db.Boolean, nullable=False, default=False)
    facilities = db.Column(JSON, nullable=False, default=list)
    hotel = db.relationship("Hotel", back_populates="profile")


class RoomType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotel.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    nightly_rate = db.Column(db.Numeric(12, 2), nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=2)
    available_rooms = db.Column(db.Integer)
    total_rooms = db.Column(db.Integer)
    price_basis = db.Column(db.String(20), nullable=False, default="unverified")
    active = db.Column(db.Boolean, nullable=False, default=True)
    hotel = db.relationship("Hotel", back_populates="rooms")


class TouristAttraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    destination_id = db.Column(db.Integer, db.ForeignKey("destination.id"), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(80), nullable=False, default="Sightseeing")
    interests = db.Column(JSON, nullable=False, default=list)
    image_url = db.Column(db.Text, nullable=False, default="")
    duration_hours = db.Column(db.Float, nullable=False, default=2)
    opening_hours = db.Column(db.String(160), nullable=False, default="")
    entry_fee = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    estimated_cost = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    best_time_to_visit = db.Column(db.String(160), nullable=False, default="")
    verification_status = db.Column(db.String(40), nullable=False, default="unverified")
    active = db.Column(db.Boolean, nullable=False, default=True)
    cost_basis = db.Column(db.String(20), nullable=False, default="unverified")
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    source_url = db.Column(db.Text, nullable=False, default="")
    destination = db.relationship("Destination", back_populates="attractions")


class TransportService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    destination_id = db.Column(db.Integer, db.ForeignKey("destination.id"), index=True, nullable=True)
    mode = db.Column(db.String(20), nullable=False, index=True)
    origin = db.Column(db.String(160), nullable=False, index=True)
    destination = db.Column(db.String(160), nullable=False, index=True)
    operator = db.Column(db.String(160), nullable=False)
    service_name = db.Column(db.String(160), nullable=False, default="")
    service_type = db.Column(db.String(100), nullable=False, default="")
    departure_time = db.Column(db.String(40), nullable=False)
    arrival_time = db.Column(db.String(40), nullable=False)
    duration = db.Column(db.String(80), nullable=False, default="")
    distance_km = db.Column(db.String(80), nullable=False, default="")
    origin_station = db.Column(db.String(160), nullable=False, default="")
    destination_station = db.Column(db.String(160), nullable=False, default="")
    available_classes = db.Column(db.String(160), nullable=False, default="")
    class_fares = db.Column(JSON, nullable=False, default=dict)
    pricing_unit = db.Column(db.String(40), nullable=False, default="per_person")
    contact_number = db.Column(db.String(80), nullable=False, default="")
    booking_url = db.Column(db.Text, nullable=False, default="")
    boarding_point = db.Column(db.String(160), nullable=False, default="")
    dropping_point = db.Column(db.String(160), nullable=False, default="")
    booking_status = db.Column(db.String(80), nullable=False, default="Available")
    is_daily = db.Column(db.Boolean, nullable=False, default=True)
    service_date = db.Column(db.Date, nullable=False, index=True)
    ticket_price = db.Column(db.Numeric(12, 2), nullable=False)
    available_seats = db.Column(db.Integer)
    availability_verified = db.Column(db.Boolean, nullable=False, default=False)
    source_url = db.Column(db.Text, nullable=False, default="")
    availability_updated_at = db.Column(db.DateTime(timezone=True), nullable=False,
                                         default=lambda: datetime.now(timezone.utc))
    active = db.Column(db.Boolean, nullable=False, default=True)
    price_basis = db.Column(db.String(20), nullable=False, default="unverified")
    is_demo = db.Column(db.Boolean, nullable=False, default=False)


class TransportReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("transport_service.id"), nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc), index=True)
    service = db.relationship("TransportService")
    user = db.relationship("User")


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    destination_id = db.Column(db.Integer, db.ForeignKey("destination.id"), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotel.id"), nullable=False)
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_type.id"))
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    rooms_count = db.Column(db.Integer, nullable=False, default=1)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    booking_reference = db.Column(db.String(40), nullable=False, default="", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    customer = db.relationship("User")
    destination = db.relationship("Destination")
    hotel = db.relationship("Hotel")
    room_type = db.relationship("RoomType")
    payments = db.relationship("Payment", back_populates="booking", lazy="select")


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    paid_at = db.Column(db.DateTime(timezone=True))
    booking = db.relationship("Booking", back_populates="payments")


class SavedItinerary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    destination_id = db.Column(db.Integer, db.ForeignKey("destination.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    days = db.Column(db.Integer, nullable=False, default=1)
    travelers = db.Column(db.Integer, nullable=False, default=1)
    budget_per_person = db.Column(db.Numeric(12, 2), nullable=False)
    total_budget = db.Column(db.Numeric(12, 2), nullable=False)
    estimated_accommodation = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    estimated_transport = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    estimated_food = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    estimated_sightseeing = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_estimated_cost = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    cost_per_person = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    remaining_budget = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    within_budget = db.Column(db.Boolean, nullable=False, default=True)
    itinerary_data = db.Column(JSON, nullable=False)
    generation_mode = db.Column(db.String(50), nullable=False, default="rule_based")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    user = db.relationship("User")
    destination = db.relationship("Destination")


def available_rooms_for_stay(room_type: RoomType, check_in: date, check_out: date) -> int:
    inventory = room_type.total_rooms
    if inventory is None:
        inventory = room_type.available_rooms
    if inventory is None:
        return 0

    reservations = Booking.query.filter(
        Booking.room_type_id == room_type.id,
        Booking.status != "cancelled",
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    ).all()
    occupancy_changes = {}
    for booking in reservations:
        occupancy_changes[booking.check_in] = (
            occupancy_changes.get(booking.check_in, 0) + booking.rooms_count
        )
        occupancy_changes[booking.check_out] = (
            occupancy_changes.get(booking.check_out, 0) - booking.rooms_count
        )

    occupied = 0
    peak_occupancy = 0
    for change_date in sorted(occupancy_changes):
        occupied += occupancy_changes[change_date]
        if change_date <= check_in:
            peak_occupancy = occupied
        if check_in <= change_date < check_out:
            peak_occupancy = max(peak_occupancy, occupied)
    return max(0, inventory - peak_occupancy)


def hotel_room_is_bookable(hotel: Hotel, room_type: RoomType) -> bool:
    if room_type.nightly_rate <= 0:
        return False
    if room_type.price_basis == "estimate":
        return True
    return (
        not hotel.is_demo
        and hotel.price_basis == "verified"
        and hotel.nightly_rate > 0
        and hotel.source_url.startswith("https://")
        and room_type.price_basis == "verified"
    )


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://tourism_app:change-me@localhost:5432/tourism_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key or secret_key == "development-only-change-this":
        raise RuntimeError("Set a strong JWT_SECRET_KEY in backend/.env before starting the API.")
    app.config["JWT_SECRET_KEY"] = secret_key
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "60"))
    )
    db.init_app(app)
    jwt.init_app(app)
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    frontend_origins = [frontend_origin]
    parsed_origin = urlsplit(frontend_origin)
    loopback_alias = {"localhost": "127.0.0.1", "127.0.0.1": "localhost"}.get(parsed_origin.hostname)
    if loopback_alias:
        netloc = f"{loopback_alias}:{parsed_origin.port}" if parsed_origin.port else loopback_alias
        frontend_origins.append(urlunsplit((
            parsed_origin.scheme, netloc, parsed_origin.path, parsed_origin.query, parsed_origin.fragment,
        )))
    CORS(app, resources={r"/api/*": {"origins": frontend_origins}})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="Not found"), 404

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify(error=getattr(error, "description", "Invalid request")), 400

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/auth/register")
    def register():
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        password = data.get("password")
        if not name or len(name) > 120 or not valid_email(email) or not valid_password(password):
            return jsonify(error="Provide a name, valid email, and password of at least 10 characters."), 400
        if User.query.filter_by(email=email).first():
            return jsonify(error="An account with this email already exists."), 409
        user = User(name=name, email=email, password_hash=generate_password_hash(password), role="customer")
        db.session.add(user)
        db.session.commit()
        return jsonify(message="Account created. Please sign in."), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        identifier = str(data.get("email", "")).strip().lower()
        password = data.get("password")
        requested_role = data.get("role")
        user = User.query.filter_by(email=identifier).first() if "@" in identifier else None
        if not user and requested_role == "admin" and identifier:
            matches = User.query.filter(
                User.role == "admin", func.lower(User.name) == identifier
            ).limit(2).all()
            user = matches[0] if len(matches) == 1 else None
        if not user or not isinstance(password, str) or not check_password_hash(user.password_hash, password):
            return jsonify(error="Invalid email or password."), 401
        if requested_role not in ("customer", "admin") or user.role != requested_role:
            return jsonify(error="This account is not authorized for that sign-in page."), 403
        from flask_jwt_extended import create_access_token

        token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
        return jsonify(token=token, user={"id": user.id, "name": user.name, "email": user.email, "role": user.role})

    @app.get("/api/destinations")
    def destinations():
        query = Destination.query.filter_by(active=True)
        search = request.args.get("search", "").strip()
        if search:
            query = query.filter(or_(
                Destination.name.ilike(f"%{search}%"),
                Destination.region.ilike(f"%{search}%"),
                Destination.state.ilike(f"%{search}%"),
                Destination.description.ilike(f"%{search}%"),
            ))
        region = request.args.get("region", "").strip()
        if region and region.lower() != "all":
            query = query.filter(or_(
                Destination.region.ilike(f"%{region}%"),
                Destination.state.ilike(f"%{region}%"),
            ))
        state = request.args.get("state", "").strip()
        if state and state.lower() != "all":
            query = query.filter(Destination.state.ilike(f"%{state}%"))
        rows = query.order_by(Destination.name).all()
        return jsonify([destination_json(row, include_attractions=True) for row in rows])

    @app.get("/api/destinations/<int:item_id>")
    def get_destination_detail(item_id: int):
        dest = Destination.query.filter_by(id=item_id, active=True).first()
        if not dest:
            return jsonify(error="Destination not found."), 404
        return jsonify(destination_json(dest, include_attractions=True))

    @app.get("/api/hotels")
    def hotels():
        query = Hotel.query.join(Destination).filter(
            Hotel.active.is_(True), Destination.active.is_(True)
        )
        destination_id = request.args.get("destination_id", type=int)
        if destination_id:
            query = query.filter(Hotel.destination_id == destination_id)
        return jsonify([hotel_json(row) for row in query.order_by(Hotel.name).all()])

    @app.get("/api/hotels/<int:hotel_id>/availability")
    def hotel_availability(hotel_id: int):
        try:
            room_type_id = int(request.args.get("room_type_id", ""))
            check_in = date.fromisoformat(request.args.get("check_in", ""))
            check_out = date.fromisoformat(request.args.get("check_out", ""))
        except (TypeError, ValueError):
            return jsonify(error="Choose a room type and valid check-in/check-out dates."), 400
        if check_in < date.today() or check_out <= check_in:
            return jsonify(error="Choose future dates and a check-out date after check-in."), 400

        hotel = Hotel.query.join(Destination).filter(
            Hotel.id == hotel_id,
            Hotel.active.is_(True),
            Destination.active.is_(True),
        ).first()
        if not hotel:
            return jsonify(error="This hotel is not available."), 404
        room_type = RoomType.query.filter_by(
            id=room_type_id, hotel_id=hotel.id, active=True
        ).first()
        if not room_type or not hotel_room_is_bookable(hotel, room_type):
            return jsonify(error="Choose a priced, bookable room type for this hotel."), 409

        available = available_rooms_for_stay(room_type, check_in, check_out)
        nights = (check_out - check_in).days
        return jsonify(
            hotel_id=hotel.id,
            room_type_id=room_type.id,
            check_in=check_in.isoformat(),
            check_out=check_out.isoformat(),
            nights=nights,
            nightly_rate=float(room_type.nightly_rate),
            total_rooms=room_type.total_rooms if room_type.total_rooms is not None else room_type.available_rooms,
            available_rooms=available,
            available=available > 0,
            is_demo=hotel.is_demo or room_type.price_basis == "estimate",
        )

    @app.get("/api/attractions")
    def attractions():
        query = TouristAttraction.query.join(Destination).filter(
            TouristAttraction.active.is_(True), Destination.active.is_(True)
        )
        destination_id = request.args.get("destination_id", type=int)
        if destination_id:
            query = query.filter(TouristAttraction.destination_id == destination_id)
        category = request.args.get("category", "").strip()
        if category and category.lower() != "all":
            query = query.filter(func.lower(TouristAttraction.category) == category.lower())
        search = request.args.get("search", "").strip()
        if search:
            query = query.filter(or_(
                TouristAttraction.name.ilike(f"%{search}%"),
                TouristAttraction.description.ilike(f"%{search}%"),
                Destination.name.ilike(f"%{search}%"),
            ))
        return jsonify([attraction_json(row) for row in query.order_by(TouristAttraction.name).all()])

    @app.get("/api/attractions/<int:item_id>")
    def get_attraction_detail(item_id: int):
        row = TouristAttraction.query.filter_by(id=item_id, active=True).first()
        if not row:
            return jsonify(error="Place not found."), 404
        return jsonify(attraction_json(row))

    CITY_ALIASES = {
        "bengaluru": ["bengaluru", "bangalore", "blr", "sbc", "ypr", "majestic", "yesvantpur"],
        "hyderabad": ["hyderabad", "secunderabad", "hyd", "sc", "kcg", "kacheguda", "cyberabad", "ameerpet"],
        "goa": ["goa", "madgaon", "vasco", "panaji", "mapusa", "colva", "mao", "vsg"],
        "chennai": ["chennai", "madras", "mas", "ms", "koyambedu", "cmbt"],
        "mumbai": ["mumbai", "bombay", "csmt", "bct", "dadar", "borivali", "vashi", "chembur", "sion"],
        "delhi": ["delhi", "new delhi", "ndls", "nzm", "dee", "ncr", "kashmere gate", "anand vihar", "sarai kale khan"],
        "agra": ["agra", "agc", "idgah", "tajganj"],
        "jaipur": ["jaipur", "jp", "pink city", "sindhi camp"],
        "ooty": ["ooty", "udhagamandalam", "mettupalayam", "mtp", "uam", "nilgiri"],
        "mysuru": ["mysuru", "mysore", "mys"],
        "kochi": ["kochi", "cochin", "ernakulam", "ers", "aluva", "kerala"],
        "kerala": ["kerala", "kochi", "cochin", "ernakulam", "ers", "aluva"],
        "manali": ["manali", "kullu"],
        "varanasi": ["varanasi", "banaras", "benares", "bsb", "kashi"],
        "rishikesh": ["rishikesh", "haridwar", "hw"],
        "tamil nadu": ["tamil nadu"],
        "munnar": ["munnar"],
        "pune": ["pune"],
    }

    def get_city_alias_terms(city_input: str) -> list[str]:
        clean = (city_input or "").strip().lower()
        if not clean:
            return []
        terms = {clean}
        for key, aliases in CITY_ALIASES.items():
            if clean == key or clean in aliases or any(clean == alias for alias in aliases):
                terms.add(key)
                terms.update(aliases)
        return list(terms)

    @app.get("/api/transport/services")
    def transport_services():
        query = TransportService.query.filter_by(active=True).filter(
            TransportService.mode.in_(("bus", "train"))
        )
        mode = (request.args.get("mode") or request.args.get("category") or "").strip().lower()
        origin = (request.args.get("from") or request.args.get("origin") or "").strip()
        destination = (request.args.get("to") or request.args.get("destination") or "").strip()
        service_date = request.args.get("date", "").strip()
        sort_by = (request.args.get("sort") or request.args.get("sort_by") or "").strip().lower()

        if mode and mode not in ("all", "*"):
            if mode not in ("bus", "train"):
                return jsonify(error="Transport options are restricted to bus and train only."), 400
            query = query.filter(TransportService.mode == mode)

        if origin and destination:
            origin_terms = get_city_alias_terms(origin)
            dest_terms = get_city_alias_terms(destination)
            direct_query = query.filter(
                func.lower(TransportService.origin).in_(origin_terms),
                func.lower(TransportService.destination).in_(dest_terms),
            )
            if direct_query.count() > 0:
                query = direct_query
            else:
                orig_clauses = [
                    func.lower(TransportService.origin).in_(origin_terms),
                    func.lower(TransportService.origin_station).like(f"%{origin.lower()}%"),
                    func.lower(TransportService.boarding_point).like(f"%{origin.lower()}%"),
                ]
                dest_clauses = [
                    func.lower(TransportService.destination).in_(dest_terms),
                    func.lower(TransportService.destination_station).like(f"%{destination.lower()}%"),
                    func.lower(TransportService.dropping_point).like(f"%{destination.lower()}%"),
                ]
                query = query.filter(or_(*orig_clauses)).filter(or_(*dest_clauses))
        elif origin:
            origin_terms = get_city_alias_terms(origin)
            query = query.filter(or_(
                func.lower(TransportService.origin).in_(origin_terms),
                func.lower(TransportService.origin_station).like(f"%{origin.lower()}%"),
                func.lower(TransportService.boarding_point).like(f"%{origin.lower()}%"),
            ))
        elif destination:
            dest_terms = get_city_alias_terms(destination)
            query = query.filter(or_(
                func.lower(TransportService.destination).in_(dest_terms),
                func.lower(TransportService.destination_station).like(f"%{destination.lower()}%"),
                func.lower(TransportService.dropping_point).like(f"%{destination.lower()}%"),
            ))

        if service_date:
            try:
                selected_date = date.fromisoformat(service_date)
            except ValueError:
                return jsonify(error="Travel date must use YYYY-MM-DD."), 400
            query = query.filter(or_(
                TransportService.service_date == selected_date,
                TransportService.is_daily.is_(True)
            ))

        if sort_by in ("highest", "expensive", "fare_desc"):
            query = query.order_by(TransportService.ticket_price.desc())
        elif sort_by in ("departure", "departure_asc"):
            query = query.order_by(TransportService.departure_time.asc())
        elif sort_by in ("fastest", "duration"):
            query = query.order_by(TransportService.duration.asc())
        elif sort_by in ("cheapest", "lowest"):
            query = query.order_by(TransportService.ticket_price.asc())
        else:
            query = query.order_by(TransportService.departure_time.asc(), TransportService.ticket_price.asc())

        rows = query.all()
        return jsonify([transport_service_json(row) for row in rows])

    @app.get("/api/transport/services/<int:service_id>")
    def get_transport_service_detail(service_id: int):
        service = db.session.get(TransportService, service_id)
        if not service or not service.active:
            return jsonify(error="Transport service not found or inactive."), 404
        return jsonify(transport_service_json(service))

    @app.post("/api/transport/reservations")
    @jwt_required()
    @customer_required
    def reserve_transport():
        data = request.get_json(silent=True) or {}
        try:
            service_id = int(data.get("service_id"))
            seats = int(data.get("seats", 1))
        except (TypeError, ValueError):
            return jsonify(error="Choose a valid service and seat count."), 400
        if not 1 <= seats <= 10:
            return jsonify(error="Seat count must be between 1 and 10."), 400
        service = db.session.get(TransportService, service_id)
        if not service:
            return jsonify(error="This bus/train service is not available for reservation."), 400
        if service.is_demo:
            return jsonify(error="Demonstration services cannot be booked."), 409
        if not service.active or service.mode not in ("bus", "train"):
            return jsonify(error="This bus/train service is not available for reservation."), 400
        if service.service_date < date.today():
            return jsonify(error="This service date has passed."), 400
        if not service.availability_verified or service.price_basis != "verified" or not service.source_url.startswith("https://"):
            return jsonify(error="Confirm the fare and seat count with a source URL before requesting seats."), 409
        if service.available_seats is None:
            return jsonify(error="Seat availability has not been provided for this service."), 409
        reserved = db.session.execute(
            update(TransportService)
            .where(
                TransportService.id == service_id,
                TransportService.active.is_(True),
                TransportService.available_seats >= seats,
            )
            .values(
                available_seats=TransportService.available_seats - seats,
                availability_updated_at=datetime.now(timezone.utc),
            )
        )
        if reserved.rowcount != 1:
            db.session.rollback()
            return jsonify(error="There are not enough seats remaining."), 409
        reservation = TransportReservation(
            user_id=int(get_jwt_identity()), service_id=service.id, seats=seats,
            amount=service.ticket_price * seats,
        )
        db.session.add(reservation)
        db.session.commit()
        return jsonify(reservation=transport_reservation_json(reservation)), 201

    @app.get("/api/transport/reservations")
    @jwt_required()
    @customer_required
    def my_transport_reservations():
        rows = TransportReservation.query.filter_by(
            user_id=int(get_jwt_identity())
        ).order_by(TransportReservation.created_at.desc()).all()
        return jsonify([transport_reservation_json(row) for row in rows])

    @app.delete("/api/transport/reservations/<int:reservation_id>")
    @jwt_required()
    @customer_required
    def cancel_transport_reservation(reservation_id: int):
        reservation = TransportReservation.query.filter_by(
            id=reservation_id, user_id=int(get_jwt_identity())
        ).first()
        if not reservation:
            return jsonify(error="Transport reservation not found."), 404
        cancelled = db.session.execute(
            update(TransportReservation)
            .where(
                TransportReservation.id == reservation_id,
                TransportReservation.user_id == int(get_jwt_identity()),
                TransportReservation.status == "pending",
            )
            .values(status="cancelled")
        )
        if cancelled.rowcount != 1:
            db.session.rollback()
            return jsonify(error="Only pending transport requests can be cancelled."), 409
        service = db.session.get(TransportService, reservation.service_id)
        if service and service.available_seats is not None:
            db.session.execute(
                update(TransportService)
                .where(TransportService.id == service.id)
                .values(
                    available_seats=TransportService.available_seats + reservation.seats,
                    availability_updated_at=datetime.now(timezone.utc),
                )
            )
        db.session.commit()
        return jsonify(message="Transport request cancelled and listed seats released.")

    @app.post("/api/assistant/recommendations")
    @jwt_required()
    @customer_required
    def budget_recommendations():
        data = request.get_json(silent=True) or {}
        try:
            budget = Decimal(str(data.get("budget_per_person", "")))
            nights = int(data.get("nights", 2))
            travelers = int(data.get("travelers", 1))
            destination_value = data.get("destination_id")
            destination_id = (
                int(destination_value)
                if destination_value is not None and destination_value != ""
                else None
            )
        except (InvalidOperation, TypeError, ValueError):
            return jsonify(error="Enter a valid per-person budget, destination, number of nights, and traveler count."), 400

        if not budget.is_finite() or budget <= 0 or budget > Decimal("10000000"):
            return jsonify(error="Per-person budget must be between ₹1 and ₹10,000,000."), 400
        if not 1 <= nights <= 30 or not 1 <= travelers <= 20:
            return jsonify(error="Choose 1–30 nights and 1–20 travelers."), 400

        listings_query = Hotel.query.join(Destination).filter(
            Hotel.active.is_(True), Destination.active.is_(True),
            Hotel.price_basis.in_(("verified", "estimate")), Hotel.nightly_rate > 0,
        )
        if destination_id is not None:
            if not Destination.query.filter_by(id=destination_id, active=True).first():
                return jsonify(error="Choose an available destination."), 400
            listings_query = listings_query.filter(Hotel.destination_id == destination_id)
        listings = listings_query.order_by(Hotel.nightly_rate, Destination.name, Hotel.name).all()

        recommendations = []
        for hotel in listings:
            room_rates = [
                (room.id, room.name, room.nightly_rate)
                for room in hotel.rooms
                if room.active and room.price_basis in ("verified", "estimate")
                and room.nightly_rate > 0 and room.capacity >= travelers and room.available_rooms != 0
            ]
            if not any(room.active for room in hotel.rooms):
                room_rates = [(None, "Listed hotel rate", hotel.nightly_rate)]
            for room_id, room_name, nightly_rate in room_rates:
                total = (nightly_rate * nights).quantize(Decimal("0.01"))
                per_person = (total / travelers).quantize(Decimal("0.01"))
                price_basis = next(
                    (room.price_basis for room in hotel.rooms if room.id == room_id),
                    hotel.price_basis,
                )
                recommendations.append({
                    "destination_id": hotel.destination.id,
                    "destination": hotel.destination.name,
                    "region": hotel.destination.region,
                    "description": hotel.destination.description,
                    "image_url": hotel.destination.image_url,
                    "hotel_id": hotel.id,
                    "hotel": hotel.name,
                    "price_tier": hotel.price_tier,
                    "price_basis": price_basis,
                    "is_demo": hotel.is_demo,
                    "room_type_id": room_id,
                    "room_type": room_name,
                    "nightly_rate": float(nightly_rate),
                    "nights": nights,
                    "travelers": travelers,
                    "estimated_total": float(total),
                    "estimated_per_person": float(per_person),
                    "within_budget": per_person <= budget,
                    "remaining_per_person": float(max(Decimal("0"), budget - per_person)),
                    "over_budget_per_person": float(max(Decimal("0"), per_person - budget)),
                })

        recommendations.sort(key=lambda option: (
            not option["within_budget"], option["estimated_per_person"], option["destination"]
        ))
        matches = [option for option in recommendations if option["within_budget"]]
        return jsonify(
            budget_per_person=float(budget),
            destination_id=destination_id,
            nights=nights,
            travelers=travelers,
            matches=matches,
            alternatives=recommendations[:3] if not matches else [],
            lodging_only=True,
            message=(
                f"Found {len(matches)} stay options within your per-person lodging budget."
                if matches else
                "No available stay fits this per-person lodging budget. Here are the closest priced options."
                if recommendations else
                "There are no active hotels to compare yet. Ask the admin to add destinations and hotels."
            ),
        )

    @app.post("/api/assistant/trip-recommendations")
    @jwt_required()
    @customer_required
    def trip_recommendations():
        data = request.get_json(silent=True) or {}
        try:
            destination_id = int(data.get("destination_id"))
            travelers = int(data.get("travelers", 1))
            budget = Decimal(str(data.get("budget_per_person", "")))
            start_date = date.fromisoformat(str(data.get("start_date", "")))
            end_date = date.fromisoformat(str(data.get("end_date", "")))
        except (InvalidOperation, TypeError, ValueError):
            return jsonify(error="Provide a destination, travel dates, traveler count, and valid per-person budget."), 400
        interests = data.get("interests", [])
        if not isinstance(interests, list) or any(not isinstance(item, str) for item in interests):
            return jsonify(error="Interests must be a list of text values."), 400
        if not budget.is_finite() or not Decimal("1") <= budget <= Decimal("10000000"):
            return jsonify(error="Trip budget per person must be between ₹1 and ₹10,000,000."), 400
        if not 1 <= travelers <= 20 or not date.today() <= start_date < end_date:
            return jsonify(error="Choose future travel dates and between 1 and 20 travelers."), 400
        nights = (end_date - start_date).days
        if nights > 30:
            return jsonify(error="Trip duration must not exceed 30 nights."), 400
        destination = Destination.query.filter_by(id=destination_id, active=True).first()
        if not destination:
            return jsonify(error="Choose an available destination."), 400
        origin = str(data.get("origin", "")).strip()
        if len(origin) > 160:
            return jsonify(error="Starting place must be 160 characters or fewer."), 400
        selected_interests = {item.strip().casefold() for item in interests if item.strip()}

        hotels = Hotel.query.filter(
            Hotel.destination_id == destination.id,
            Hotel.active.is_(True),
            Hotel.is_demo.is_(False),
            Hotel.price_basis.in_(("verified", "estimate")),
            Hotel.nightly_rate > 0,
        ).all()
        unpriced_hotels = Hotel.query.filter(
            Hotel.destination_id == destination.id,
            Hotel.active.is_(True),
            Hotel.is_demo.is_(False),
            or_(Hotel.price_basis.notin_(("verified", "estimate")), Hotel.nightly_rate <= 0),
        ).order_by(Hotel.name).all()
        options_by_tier = {}
        for hotel in hotels:
            eligible_rooms = []
            for room in hotel.rooms:
                if not room.active or room.price_basis not in ("verified", "estimate") or room.nightly_rate <= 0:
                    continue
                room_count = (travelers + room.capacity - 1) // room.capacity
                if room.available_rooms is None or room.available_rooms >= room_count:
                    eligible_rooms.append(room)
            if eligible_rooms:
                room = min(eligible_rooms, key=lambda item: item.nightly_rate)
                room_count = (travelers + room.capacity - 1) // room.capacity
                nightly_cost = room.nightly_rate * room_count
                room_name = room.name
            elif not any(room.active for room in hotel.rooms):
                room = None
                room_count = travelers
                nightly_cost = hotel.nightly_rate * room_count
                room_name = "Listed hotel rate"
            else:
                continue
            total = (nightly_cost * nights).quantize(Decimal("0.01"))
            per_person = (total / travelers).quantize(Decimal("0.01"))
            tier = hotel.price_tier if hotel.price_tier in ("budget", "mid-range", "luxury") else "unclassified"
            option = {
                "hotel_id": hotel.id, "hotel": hotel.name, "price_tier": tier,
                "price_basis": room.price_basis if room else hotel.price_basis, "is_demo": hotel.is_demo,
                "source_url": hotel.source_url,
                "room_type_id": room.id if room else None, "room_type": room_name,
                "rooms_required": room_count,
                "nightly_rate_per_room": float(room.nightly_rate if room else hotel.nightly_rate),
                "estimated_total": float(total), "estimated_per_person": float(per_person),
            }
            current = options_by_tier.get(tier)
            if current is None or per_person < Decimal(str(current["estimated_per_person"])):
                options_by_tier[tier] = option
        accommodation_options = list(options_by_tier.values())

        transport_query = TransportService.query.filter(
            TransportService.active.is_(True),
            TransportService.service_date >= start_date,
            TransportService.service_date <= end_date,
        )
        if origin:
            transport_query = transport_query.filter(
                func.lower(TransportService.origin) == origin.casefold()
            )
        transport_query = transport_query.filter(
            or_(
                TransportService.destination_id == destination.id,
                func.lower(TransportService.destination) == destination.name.casefold(),
            )
        )
        transport_rows = transport_query.order_by(TransportService.ticket_price).all()
        transport_options = []
        for service in transport_rows:
            per_person = Decimal(service.ticket_price)
            if service.mode in ("taxi", "transfer") and "vehicle" in service.service_type.casefold():
                per_person /= travelers
            transport_options.append({
                "service_id": service.id, "mode": service.mode,
                "origin": service.origin, "destination": service.destination,
                "operator": service.operator, "service_name": service.service_name,
                "service_date": service.service_date.isoformat(),
                "price_basis": service.price_basis, "is_demo": service.is_demo,
                "source_url": service.source_url,
                "availability_verified": service.availability_verified,
                "available_seats": service.available_seats,
                "estimated_cost_per_person": float(per_person.quantize(Decimal("0.01"))),
            })
        transport_options.sort(key=lambda item: item["estimated_cost_per_person"])

        attractions = TouristAttraction.query.filter_by(
            destination_id=destination.id, active=True
        ).all()
        if selected_interests:
            attractions = [
                place for place in attractions
                if selected_interests.intersection(
                    item.casefold() for item in (place.interests or [])
                )
            ]
        attractions.sort(key=lambda place: (
            -len(selected_interests.intersection(
                item.casefold() for item in (place.interests or [])
            )),
            Decimal(place.estimated_cost),
            place.name.casefold(),
        ))
        attraction_options = [attraction_json(place) for place in attractions[:5]]
        cheapest_transport = transport_options[0] if transport_options else None
        transport_cost_complete = bool(
            cheapest_transport
            and not cheapest_transport["is_demo"]
            and cheapest_transport["price_basis"] in ("verified", "estimate")
            and cheapest_transport["source_url"].startswith("https://")
        )
        for option in accommodation_options:
            transport_cost = Decimal(str(
                cheapest_transport["estimated_cost_per_person"] if cheapest_transport else 0
            ))
            activity_cost = sum(
                Decimal(str(place["estimated_cost"]))
                for place in attraction_options
                if place["cost_basis"] in ("verified", "free")
            )
            activity_cost_complete = all(
                place["cost_basis"] in ("verified", "free")
                for place in attraction_options
            ) and bool(attraction_options)
            estimated = Decimal(str(option["estimated_per_person"])) + transport_cost + activity_cost
            option.update(
                estimated_transport_per_person=float(transport_cost),
                estimated_activities_per_person=float(activity_cost),
                estimated_trip_per_person=float(estimated.quantize(Decimal("0.01"))),
                estimate_complete=(
                    transport_cost_complete
                    and activity_cost_complete
                    and option["price_basis"] in ("verified", "estimate")
                ),
                within_budget=(
                    transport_cost_complete
                    and activity_cost_complete
                    and option["price_basis"] in ("verified", "estimate")
                    and estimated <= budget
                ),
            )
        accommodation_options.sort(key=lambda item: (
            item["estimated_trip_per_person"], item["price_tier"], item["hotel"]
        ))
        return jsonify(
            destination=destination_json(destination),
            origin=origin,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            nights=nights,
            travelers=travelers,
            budget_per_person=float(budget),
            accommodation_options=accommodation_options,
            unpriced_accommodations=[{
                "hotel_id": hotel.id,
                "hotel": hotel.name,
                "price_tier": hotel.price_tier,
                "source_url": hotel.source_url,
            } for hotel in unpriced_hotels],
            transport_options=transport_options[:5],
            transport_estimate_available=cheapest_transport is not None,
            transport_estimate_complete=transport_cost_complete,
            attractions=attraction_options,
            transport_message=(
                "No catalog route matches this starting place, destination, and travel date."
                if not transport_options else
                "Transport estimates use matching catalog records; confirm schedules and prices with the provider."
            ),
            pricing_notice="Property names link to their public sources. Unavailable prices, transport data, and visitor fees are excluded rather than guessed.",
        )

    @app.post("/api/assistant/itinerary")
    @jwt_required()
    @customer_required
    def create_itinerary():
        data = request.get_json(silent=True) or {}
        try:
            destination_id = int(data.get("destination_id"))
            days = int(data.get("days", 1))
            budget = Decimal(str(data.get("budget_per_person", "")))
        except (InvalidOperation, TypeError, ValueError):
            return jsonify(error="Choose a destination, trip length, and valid total activity budget per person."), 400
        interests = data.get("interests", [])
        if not isinstance(interests, list) or any(not isinstance(item, str) for item in interests):
            return jsonify(error="Interests must be a list of text values."), 400
        interests = {item.strip().casefold() for item in interests if item.strip()}
        if not budget.is_finite() or budget < 0 or budget > Decimal("10000000"):
            return jsonify(error="Activity budget per person must be between ₹0 and ₹10,000,000."), 400
        if not 1 <= days <= 14:
            return jsonify(error="Trip length must be between 1 and 14 days."), 400
        destination = Destination.query.filter_by(id=destination_id, active=True).first()
        if not destination:
            return jsonify(error="Choose an available destination."), 400

        places = TouristAttraction.query.filter_by(destination_id=destination.id, active=True).all()
        ranked_places = sorted(
            places,
            key=lambda place: (
                -len(interests.intersection(item.casefold() for item in (place.interests or []))),
                Decimal(place.estimated_cost) if place.cost_basis in ("verified", "free") else Decimal("0"),
                place.name.casefold(),
            ),
        )
        itinerary = [{"day": day, "places": [], "estimated_cost": 0.0} for day in range(1, days + 1)]
        selected_cost = Decimal("0")
        selected_places = []
        for index, place in enumerate(ranked_places):
            if index >= days * 3:
                break
            cost = Decimal(place.estimated_cost) if place.cost_basis in ("verified", "free") else Decimal("0")
            if selected_cost + cost > budget:
                continue
            day = itinerary[index % days]
            day["places"].append(attraction_json(place))
            selected_places.append(place)
            day["estimated_cost"] = float(Decimal(str(day["estimated_cost"])) + cost)
            selected_cost += cost

        return jsonify(
            destination=destination_json(destination),
            days=days,
            interests=sorted(interests),
            budget_per_person=float(budget),
            estimated_activity_cost=float(selected_cost),
            activity_cost_complete=bool(selected_places) and all(
                place.cost_basis in ("verified", "free") for place in selected_places
            ),
            lodging_and_transport_included=False,
            itinerary=itinerary,
            message=(
                "Suggested from destination places in the catalog, matched to your interests and activity budget."
                if places else
                "There are no tourist places in this destination's catalog yet. Ask the admin to add places before planning an itinerary."
            ),
        )

    def calculate_destination_estimate(dest: Destination, days: int, travelers: int, budget_per_person: Decimal) -> dict:
        attractions = [a for a in dest.attractions if a.active]
        rooms_needed = math.ceil(travelers / 2)
        nights = max(1, days - 1) if days > 1 else 1

        hotels = Hotel.query.filter_by(destination_id=dest.id, active=True).all()
        valid_rates = [float(h.nightly_rate) for h in hotels if h.nightly_rate and h.nightly_rate > 0]
        for h in hotels:
            for r in h.rooms:
                if r.active and r.nightly_rate and r.nightly_rate > 0:
                    valid_rates.append(float(r.nightly_rate))

        if valid_rates:
            valid_rates.sort()
            hotel_rate = Decimal(str(valid_rates[len(valid_rates) // 3]))
        else:
            hotel_rate = Decimal("2800.00")

        est_accommodation = (hotel_rate * rooms_needed * nights).quantize(Decimal("0.01"))
        est_transport = (Decimal("450.00") * travelers * days).quantize(Decimal("0.01"))
        est_food = (Decimal("750.00") * travelers * days).quantize(Decimal("0.01"))

        entry_fees = [Decimal(str(a.entry_fee if a.entry_fee is not None else a.estimated_cost)) for a in attractions]
        if entry_fees:
            avg_entry = sum(entry_fees) / Decimal(str(len(entry_fees)))
        else:
            avg_entry = Decimal("25.00")

        sights_per_trip = min(days * 2, max(2, len(attractions)))
        est_sightseeing = (avg_entry * sights_per_trip * travelers).quantize(Decimal("0.01"))

        total_estimated_cost = est_accommodation + est_transport + est_food + est_sightseeing
        cost_per_person = (total_estimated_cost / travelers).quantize(Decimal("0.01"))
        total_budget = budget_per_person * travelers
        remaining_budget = (total_budget - total_estimated_cost).quantize(Decimal("0.01"))
        within_budget = remaining_budget >= Decimal("0")

        if within_budget:
            match_reason = f"Comfortably fits your budget with an estimated ₹{cost_per_person:,.0f}/person, leaving a ₹{remaining_budget:,.0f} buffer for shopping and activities."
        else:
            deficit = abs(remaining_budget)
            match_reason = f"High demand travel destination; requires approx ₹{deficit:,.0f} additional budget for standard lodging and full sightseeing."

        return {
            "destination_id": dest.id,
            "destination_name": dest.name,
            "hotel_rate": hotel_rate,
            "rooms_needed": rooms_needed,
            "nights": nights,
            "estimated_accommodation": est_accommodation,
            "estimated_transport": est_transport,
            "estimated_food": est_food,
            "estimated_sightseeing": est_sightseeing,
            "total_estimated_cost": total_estimated_cost,
            "cost_per_person": cost_per_person,
            "total_budget": total_budget,
            "remaining_budget": remaining_budget,
            "within_budget": within_budget,
            "attractions_count": len(attractions),
            "match_reason": match_reason,
        }

    def build_detailed_itinerary(
        dest: Destination,
        days: int,
        travelers: int,
        budget_per_person: Decimal,
        interests: set[str],
        recommended_destinations: list,
        origin: str = "",
    ) -> dict:
        est = calculate_destination_estimate(dest, days, travelers, budget_per_person)
        attractions = [a for a in dest.attractions if a.active]

        def score_attraction(a):
            score = 0
            cat = (a.category or "").casefold()
            name = (a.name or "").casefold()
            desc = (a.description or "").casefold()
            a_interests = [item.casefold() for item in (a.interests or [])]
            for interest in interests:
                if interest in cat or cat in interest:
                    score += 5
                if any(interest in item or item in interest for item in a_interests):
                    score += 5
                if interest in name or interest in desc:
                    score += 2
            return score

        if interests:
            attractions.sort(key=lambda a: (-score_attraction(a), Decimal(a.entry_fee if a.entry_fee is not None else 0), a.name))
        else:
            attractions.sort(key=lambda a: (Decimal(a.entry_fee if a.entry_fee is not None else 0), a.name))

        daily_schedule = []
        attraction_index = 0
        total_attractions = len(attractions)

        experience_fillers = [
            {
                "name": f"{dest.name} Traditional Market & Artisan Bazaar",
                "category": "Culture & Shopping",
                "description": f"Immerse yourself in the bustling local markets of {dest.name}, featuring regional crafts, authentic spices, and souvenir shopping.",
                "image_url": "https://images.unsplash.com/photo-1533900298318-6b8da08a523e?auto=format&fit=crop&w=1000&q=80",
                "duration_hours": 2.0,
                "opening_hours": "10:00 AM – 08:30 PM",
                "entry_fee": 0.0,
                "time_slot": "Evening (05:30 PM – 07:30 PM)",
                "suggested_activity": "Sample regional street delicacies, interact with local artisans, and pick up authentic handicrafts.",
            },
            {
                "name": f"{dest.name} Sunset Promenade & Leisure Walk",
                "category": "Scenic & Leisure",
                "description": f"A serene evening stroll along the most picturesque vantage points and scenic promenades of {dest.name}.",
                "image_url": "https://images.unsplash.com/photo-1495616811223-4d98c6e9c869?auto=format&fit=crop&w=1000&q=80",
                "duration_hours": 1.5,
                "opening_hours": "Open 24 hours",
                "entry_fee": 0.0,
                "time_slot": "Evening (05:30 PM – 07:30 PM)",
                "suggested_activity": "Enjoy tranquil golden hour vistas, ideal for relaxed conversation and landscape photography.",
            },
            {
                "name": f"{dest.name} Regional Cuisine & Heritage Dining Experience",
                "category": "Culinary & Dining",
                "description": f"Indulge in a curated dining experience celebrating authentic {dest.state or dest.region} flavors and specialty dishes.",
                "image_url": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=1000&q=80",
                "duration_hours": 1.5,
                "opening_hours": "12:30 PM – 10:30 PM",
                "entry_fee": 0.0,
                "time_slot": "Afternoon (01:00 PM – 02:30 PM)",
                "suggested_activity": "Taste signature local delicacies recommended by chefs and learn the culinary traditions of the region.",
            },
            {
                "name": f"{dest.name} Nature Trail & Botanical Exploration",
                "category": "Nature & Outdoors",
                "description": f"A refreshing morning walk through the lush gardens and tranquil green pathways surrounding {dest.name}.",
                "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1000&q=80",
                "duration_hours": 2.0,
                "opening_hours": "06:30 AM – 06:00 PM",
                "entry_fee": 20.0,
                "time_slot": "Morning (09:00 AM – 11:30 AM)",
                "suggested_activity": "Early birdwatching, fresh air, and capturing morning dew on indigenous flora.",
            },
        ]
        filler_index = 0
        actual_scheduled_entry_fees = Decimal("0")

        for day_num in range(1, days + 1):
            day_items = []

            # Morning slot
            if attraction_index < total_attractions:
                item = attractions[attraction_index]
                attraction_index += 1
                fee = Decimal(str(item.entry_fee if item.entry_fee is not None else item.estimated_cost))
                actual_scheduled_entry_fees += fee * travelers
                day_items.append({
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "description": item.description,
                    "image_url": item.image_url or dest.image_url,
                    "duration_hours": float(item.duration_hours or 2.0),
                    "duration_text": f"{float(item.duration_hours or 2.0):.1f} hrs",
                    "opening_hours": item.opening_hours or "09:00 AM – 05:30 PM",
                    "entry_fee": float(fee),
                    "time_slot": "Morning (09:00 AM – 12:30 PM)",
                    "suggested_activity": "Arrive early to avoid peak mid-day lines and capture the best lighting for photos.",
                    "is_custom": False,
                })
            else:
                filler = experience_fillers[filler_index % len(experience_fillers)]
                filler_index += 1
                day_items.append({
                    **filler,
                    "id": None,
                    "image_url": filler.get("image_url") or dest.image_url,
                    "duration_text": f"{filler['duration_hours']:.1f} hrs",
                    "is_custom": True,
                })

            # Afternoon slot
            if attraction_index < total_attractions:
                item = attractions[attraction_index]
                attraction_index += 1
                fee = Decimal(str(item.entry_fee if item.entry_fee is not None else item.estimated_cost))
                actual_scheduled_entry_fees += fee * travelers
                day_items.append({
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "description": item.description,
                    "image_url": item.image_url or dest.image_url,
                    "duration_hours": float(item.duration_hours or 2.0),
                    "duration_text": f"{float(item.duration_hours or 2.0):.1f} hrs",
                    "opening_hours": item.opening_hours or "09:30 AM – 06:00 PM",
                    "entry_fee": float(fee),
                    "time_slot": "Afternoon (02:00 PM – 05:00 PM)",
                    "suggested_activity": "Explore exhibits at your own pace and take a brief hydration / tea break nearby.",
                    "is_custom": False,
                })
            else:
                filler = experience_fillers[filler_index % len(experience_fillers)]
                filler_index += 1
                day_items.append({
                    **filler,
                    "id": None,
                    "image_url": filler.get("image_url") or dest.image_url,
                    "duration_text": f"{filler['duration_hours']:.1f} hrs",
                    "is_custom": True,
                })

            # Evening slot
            if attraction_index < total_attractions and total_attractions >= days * 3:
                item = attractions[attraction_index]
                attraction_index += 1
                fee = Decimal(str(item.entry_fee if item.entry_fee is not None else item.estimated_cost))
                actual_scheduled_entry_fees += fee * travelers
                day_items.append({
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "description": item.description,
                    "image_url": item.image_url or dest.image_url,
                    "duration_hours": float(item.duration_hours or 1.5),
                    "duration_text": f"{float(item.duration_hours or 1.5):.1f} hrs",
                    "opening_hours": item.opening_hours or "Open until late evening",
                    "entry_fee": float(fee),
                    "time_slot": "Evening (05:30 PM – 08:00 PM)",
                    "suggested_activity": "Enjoy the illuminated ambiance and vibrant evening atmosphere.",
                    "is_custom": False,
                })
            else:
                filler = experience_fillers[filler_index % len(experience_fillers)]
                filler_index += 1
                day_items.append({
                    **filler,
                    "id": None,
                    "image_url": filler.get("image_url") or dest.image_url,
                    "duration_text": f"{filler['duration_hours']:.1f} hrs",
                    "is_custom": True,
                })

            day_entry_sum = sum(slot["entry_fee"] for slot in day_items)
            daily_schedule.append({
                "day": day_num,
                "title": f"Day {day_num}: {day_items[0]['name'].split('(')[0].strip()} & Environs",
                "schedule": day_items,
                "day_sightseeing_cost_per_person": float(day_entry_sum),
            })

        est_sightseeing = actual_scheduled_entry_fees.quantize(Decimal("0.01"))

        # Query matching demo buses and trains for this destination and starting point
        origin_clean = str(origin).strip() if origin else ""
        transport_matches = []
        requires_origin = not bool(origin_clean)
        origin_prompt = ""
        comparison_summary = ""

        if origin_clean:
            origin_terms = get_city_alias_terms(origin_clean)
            dest_terms = get_city_alias_terms(dest.name)
            
            # Prioritize direct origin -> destination corridor match
            direct_matches = TransportService.query.filter(
                TransportService.active.is_(True),
                TransportService.mode.in_(("bus", "train")),
                func.lower(TransportService.origin).in_(origin_terms),
                func.lower(TransportService.destination).in_(dest_terms),
            ).order_by(TransportService.departure_time.asc()).all()

            if direct_matches:
                transport_matches = direct_matches
            else:
                origin_clauses = [
                    func.lower(TransportService.origin).in_(origin_terms),
                    func.lower(TransportService.origin_station).like(f"%{origin_clean.lower()}%"),
                    func.lower(TransportService.boarding_point).like(f"%{origin_clean.lower()}%"),
                ]
                dest_clauses = [
                    func.lower(TransportService.destination).in_(dest_terms),
                    func.lower(TransportService.destination_station).like(f"%{dest.name.lower()}%"),
                    func.lower(TransportService.dropping_point).like(f"%{dest.name.lower()}%"),
                ]
                transport_matches = TransportService.query.filter(
                    TransportService.active.is_(True),
                    TransportService.mode.in_(("bus", "train")),
                    or_(*origin_clauses),
                    or_(*dest_clauses),
                ).order_by(TransportService.departure_time.asc()).all()

            # Dynamic fallback: if corridor has no matches in database, generate deterministic demo services
            b_list = [t for t in transport_matches if t.mode == "bus"]
            t_list = [t for t in transport_matches if t.mode == "train"]
            if len(b_list) < 5 or len(t_list) < 5:
                try:
                    from transport_generator import generate_demo_buses_for_route, generate_demo_trains_for_route
                    if len(b_list) < 5:
                        for b_dict in generate_demo_buses_for_route(origin_clean, dest.name, dest.id):
                            b_inst = TransportService(**b_dict)
                            b_inst.id = 900000 + len(transport_matches) + 1
                            transport_matches.append(b_inst)
                    if len(t_list) < 5:
                        for t_dict in generate_demo_trains_for_route(origin_clean, dest.name, dest.id):
                            t_inst = TransportService(**t_dict)
                            t_inst.id = 950000 + len(transport_matches) + 1
                            transport_matches.append(t_inst)
                except Exception:
                    pass
        else:
            requires_origin = True
            origin_prompt = "Please enter your starting city (origin) to view matching demo buses and trains and incorporate precise transit fares into your trip budget."

        buses_matched = [t for t in transport_matches if t.mode == "bus"]
        trains_matched = [t for t in transport_matches if t.mode == "train"]
        buses_matched.sort(key=lambda b: getattr(b, "departure_time", "") or "")
        trains_matched.sort(key=lambda t: getattr(t, "departure_time", "") or "")

        rec_bus = min(buses_matched, key=lambda b: b.ticket_price) if buses_matched else None
        rec_train = min(trains_matched, key=lambda t: t.ticket_price) if trains_matched else None

        # Calculate realistic transport expenses considering matched routes
        local_daily_transit = (Decimal("250.00") * travelers * days).quantize(Decimal("0.01"))
        if origin_clean and (rec_bus or rec_train):
            intercity_fare = Decimal(str(rec_train.ticket_price if rec_train else rec_bus.ticket_price))
            transit_cost_total = (intercity_fare * travelers).quantize(Decimal("0.01"))
            est_transport = (transit_cost_total + local_daily_transit).quantize(Decimal("0.01"))
        else:
            est_transport = (Decimal("400.00") * travelers * days).quantize(Decimal("0.01"))

        total_estimated_cost = (est["estimated_accommodation"] + est_transport + est["estimated_food"] + est_sightseeing).quantize(Decimal("0.01"))
        cost_per_person = (total_estimated_cost / travelers).quantize(Decimal("0.01"))
        total_budget = (budget_per_person * travelers).quantize(Decimal("0.01"))
        remaining_budget = (total_budget - total_estimated_cost).quantize(Decimal("0.01"))
        within_budget = remaining_budget >= Decimal("0")

        # Formulate intelligent bus vs train comparison summary
        if rec_bus and rec_train:
            bus_tot = float(rec_bus.ticket_price) * travelers
            train_tot = float(rec_train.ticket_price) * travelers
            speed_lead = "Train is faster" if "h" in rec_train.duration and "h" in rec_bus.duration else "Both provide convenient schedules"
            comparison_summary = (
                f"Evaluated {len(buses_matched)} demo bus and {len(trains_matched)} demo train services connecting {origin_clean} to {dest.name}. "
                f"Train option: {rec_train.service_name} ({rec_train.duration}) at ₹{float(rec_train.ticket_price):,.0f}/person (₹{train_tot:,.0f} total). "
                f"Bus option: {rec_bus.operator} ({rec_bus.duration}) at ₹{float(rec_bus.ticket_price):,.0f}/person (₹{bus_tot:,.0f} total). "
                f"Recommendation: Choose the {'train for rapid, comfortable rail transit' if rec_train.ticket_price <= rec_bus.ticket_price * Decimal('1.35') else 'bus for overnight sleeper economy'}."
            )
        elif rec_bus:
            bus_tot = float(rec_bus.ticket_price) * travelers
            comparison_summary = (
                f"Found {len(buses_matched)} matching demo bus service(s) from {origin_clean} to {dest.name}. "
                f"Top pick: {rec_bus.operator} ({rec_bus.duration}) at ₹{float(rec_bus.ticket_price):,.0f}/person (₹{bus_tot:,.0f} total for {travelers} traveler{'s' if travelers > 1 else ''}). "
                f"No direct demo train service is currently cataloged on this corridor."
            )
        elif rec_train:
            train_tot = float(rec_train.ticket_price) * travelers
            comparison_summary = (
                f"Found {len(trains_matched)} matching demo train service(s) from {origin_clean} to {dest.name}. "
                f"Top pick: {rec_train.service_name} ({rec_train.duration}) at ₹{float(rec_train.ticket_price):,.0f}/person (₹{train_tot:,.0f} total for {travelers} traveler{'s' if travelers > 1 else ''}). "
                f"No direct demo bus service is currently cataloged on this corridor."
            )
        elif origin_clean:
            comparison_summary = (
                f"No matching demo bus or train routes currently in the database between {origin_clean} and {dest.name}. "
                f"Popular active demo corridors include Hyderabad ➔ Goa, Hyderabad ➔ Chennai, Bengaluru ➔ Mysuru, Delhi ➔ Agra, Mumbai ➔ Goa, and Chennai ➔ Ooty."
            )
        else:
            comparison_summary = "Starting location has not been provided. Please enter your starting city above to view matching bus and train schedules and compare fares."

        alternatives = []
        if within_budget:
            budget_status = "within_budget"
            budget_explanation = (
                f"Your budget of ₹{budget_per_person:,.0f} per person comfortably covers the estimated ₹{cost_per_person:,.0f} "
                f"total expense for this {days}-day trip, leaving a surplus balance of ₹{remaining_budget:,.0f}."
            )
        else:
            deficit_total = abs(remaining_budget)
            deficit_per_person = (deficit_total / travelers).quantize(Decimal("0.01"))
            budget_status = "insufficient_budget"
            budget_explanation = (
                f"Your budget of ₹{budget_per_person:,.0f} per person is short by ₹{deficit_per_person:,.0f} "
                f"(total shortfall of ₹{deficit_total:,.0f}) for this {days}-day itinerary in {dest.name}. "
                f"Estimated total trip cost is ₹{total_estimated_cost:,.0f} (₹{cost_per_person:,.0f}/person)."
            )

            if days > 1:
                shorter_days = max(1, days - 1 if days <= 3 else days - 2)
                day_saving = (est["estimated_accommodation"] / est["nights"] + Decimal("1200") * travelers)
                alternatives.append({
                    "type": "duration",
                    "title": f"Shorten trip to {shorter_days} days",
                    "description": f"Reducing your itinerary from {days} to {shorter_days} days saves approx ₹{day_saving * (days - shorter_days):,.0f} in lodging and daily expenses.",
                    "savings_estimate": float(day_saving * (days - shorter_days)),
                })

            cheaper_dests = [
                d for d in recommended_destinations
                if d.get("destination_id") != dest.id and d.get("estimated_cost_per_person", float("inf")) < float(cost_per_person)
            ]
            if cheaper_dests:
                top_cheaper = cheaper_dests[0]
                alternatives.append({
                    "type": "destination",
                    "title": f"Switch to {top_cheaper['name']}",
                    "destination_id": top_cheaper["destination_id"],
                    "description": f"{top_cheaper['name']} ({top_cheaper['state']}) estimated at only ₹{top_cheaper['estimated_cost_per_person']:,.0f}/person offers {top_cheaper['attractions_count']} attractions with lower lodging rates.",
                    "savings_estimate": float(cost_per_person) - float(top_cheaper["estimated_cost_per_person"]),
                })

            alternatives.append({
                "type": "accommodation",
                "title": "Select Budget Homestays / Hostels",
                "description": f"Choosing verified guesthouses or hostels instead of standard hotels can save up to ₹1,200 per room/night (~₹{1200 * est['nights'] * est['rooms_needed']:,.0f} total).",
                "savings_estimate": float(1200 * est["nights"] * est["rooms_needed"]),
            })

            alternatives.append({
                "type": "sightseeing",
                "title": "Focus on Complimentary Attractions",
                "description": "Swap paid monument entry tickets for scenic beaches, historic ghats, and open heritage promenades.",
                "savings_estimate": float(est_sightseeing),
            })

        has_ai_api = bool(os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY"))
        generation_mode = "ai_live" if has_ai_api else "rule_based"
        generation_label = "AI-Powered Live Generator" if has_ai_api else "Database-Driven Smart Engine (Rule-based)"

        def serialize_rec_item(item):
            if not item:
                return None
            fare = float(item.ticket_price) if item.ticket_price is not None else 0.0
            return {
                "id": item.id,
                "mode": item.mode,
                "category": item.mode,
                "operator": item.operator,
                "service_name": item.service_name or "",
                "service_type": item.service_type or "",
                "origin": item.origin,
                "origin_station": item.origin_station or "",
                "destination": item.destination,
                "destination_station": item.destination_station or "",
                "boarding_point": getattr(item, "boarding_point", "") or item.origin_station or item.origin,
                "dropping_point": getattr(item, "dropping_point", "") or item.destination_station or item.destination,
                "departure_time": item.departure_time,
                "arrival_time": item.arrival_time,
                "duration": item.duration,
                "distance_km": item.distance_km,
                "ticket_price": fare,
                "fare_per_person": fare,
                "estimated_fare_per_person": fare,
                "total_fare": round(fare * travelers, 2),
                "total_estimated_fare": round(fare * travelers, 2),
                "travelers": travelers,
                "available_seats": item.available_seats,
                "booking_status": getattr(item, "booking_status", "Available") or f"Available - {item.available_seats or 30} demo seats",
                "available_classes": item.available_classes or "",
                "class_fares": item.class_fares if isinstance(item.class_fares, dict) else {},
                "booking_url": item.booking_url or item.source_url or "",
                "is_demo": True,
            }

        rec_transport_obj = {
            "origin": origin_clean or "Starting City Not Specified",
            "destination": dest.name,
            "requires_origin": requires_origin,
            "origin_prompt": origin_prompt,
            "message": origin_prompt,
            "has_route_matches": len(transport_matches) > 0,
            "recommended_bus": serialize_rec_item(rec_bus),
            "recommended_train": serialize_rec_item(rec_train),
            "buses": [serialize_rec_item(t) for t in buses_matched],
            "trains": [serialize_rec_item(t) for t in trains_matched],
            "all_options": [serialize_rec_item(t) for t in (buses_matched + trains_matched)],
            "matched_services": [serialize_rec_item(t) for t in (buses_matched + trains_matched)],
            "comparison_summary": comparison_summary,
            "recommendation_summary": comparison_summary,
            "estimated_transport_cost": float(est_transport),
            "is_demo_notice": "Sample demo services and estimated fares for planning purposes only. Live bookings must be confirmed directly through official railway (IRCTC) or bus operator portals.",
        }

        return {
            "destination": destination_json(dest, include_attractions=True),
            "title": f"{days}-Day {dest.name} Discovery",
            "days": days,
            "travelers": travelers,
            "origin": origin_clean,
            "budget_per_person": float(budget_per_person),
            "total_budget": float(total_budget),
            "estimated_accommodation": float(est["estimated_accommodation"]),
            "accommodation_details": {
                "rooms": est["rooms_needed"],
                "nights": est["nights"],
                "nightly_rate": float(est["hotel_rate"]),
            },
            "estimated_transport": float(est_transport),
            "transport_details": {
                "daily_per_person": round(float(est_transport) / (travelers * days), 2),
                "days": days,
                "travelers": travelers,
                "origin": origin_clean or "Transit Hub",
                "destination": dest.name,
            },
            "travel_and_transport": rec_transport_obj,
            "recommended_transport": rec_transport_obj,
            "transport_options": rec_transport_obj,
            "estimated_food": float(est["estimated_food"]),
            "food_details": {
                "daily_per_person": 750.0,
                "days": days,
                "travelers": travelers,
            },
            "estimated_sightseeing": float(est_sightseeing),
            "total_estimated_cost": float(total_estimated_cost),
            "cost_per_person": float(cost_per_person),
            "remaining_budget": float(remaining_budget),
            "within_budget": within_budget,
            "budget_status": budget_status,
            "budget_explanation": budget_explanation,
            "alternatives": alternatives,
            "recommended_destinations": recommended_destinations[:6],
            "daily_schedule": daily_schedule,
            "generation_mode": generation_mode,
            "generation_label": generation_label,
            "pricing_disclaimer": "All estimated costs are synthesized from catalog attraction fees and regional lodging/transit metrics. Estimates are for travel planning and do not represent live reservation quotes.",
        }

    @app.post("/api/itineraries/generate")
    @app.post("/api/assistant/generate-itinerary")
    @jwt_required()
    @customer_required
    def generate_full_itinerary():
        data = request.get_json(silent=True) or {}
        try:
            budget = Decimal(str(data.get("budget_per_person") or data.get("budget", "")))
            days = int(data.get("days", data.get("nights", 1)))
            travelers = int(data.get("travelers", 1))
            dest_val = data.get("destination_id")
            destination_id = int(dest_val) if dest_val not in (None, "", "null") else None
        except (InvalidOperation, TypeError, ValueError):
            return jsonify(error="Provide a valid budget per person (₹), number of days (1-14), and travellers (1-20)."), 400

        if not budget.is_finite() or budget <= 0 or budget > Decimal("10000000"):
            return jsonify(error="Budget per person must be between ₹1 and ₹10,000,000."), 400
        if not 1 <= days <= 14:
            return jsonify(error="Trip duration must be between 1 and 14 days."), 400
        if not 1 <= travelers <= 20:
            return jsonify(error="Travelers must be between 1 and 20."), 400

        interests = data.get("interests", [])
        if isinstance(interests, list):
            interests_set = {str(item).strip().casefold() for item in interests if str(item).strip()}
        else:
            interests_set = set()

        selected_dest = None
        recommended_destinations = []
        if destination_id:
            selected_dest = Destination.query.filter_by(id=destination_id, active=True).first()
            if not selected_dest:
                return jsonify(error="Selected destination is not available."), 404
        else:
            all_destinations = Destination.query.filter_by(active=True).all()
            scored_destinations = []
            for dest in all_destinations:
                calc = calculate_destination_estimate(dest, days, travelers, budget)
                scored_destinations.append({
                    "destination_id": dest.id,
                    "name": dest.name,
                    "state": dest.state or dest.region,
                    "region": dest.region,
                    "image_url": dest.image_url,
                    "description": dest.description,
                    "best_time_to_visit": dest.best_time_to_visit or "October to March",
                    "budget_range": dest.budget_range,
                    "estimated_cost_per_person": float(calc["cost_per_person"]),
                    "total_estimated_cost": float(calc["total_estimated_cost"]),
                    "within_budget": calc["within_budget"],
                    "remaining_budget": float(calc["remaining_budget"]),
                    "attractions_count": calc["attractions_count"],
                    "match_reason": calc["match_reason"],
                })

            scored_destinations.sort(key=lambda item: (
                0 if item["within_budget"] else 1,
                -item["attractions_count"] if item["within_budget"] else item["estimated_cost_per_person"],
            ))
            recommended_destinations = scored_destinations
            if scored_destinations:
                selected_dest = db.session.get(Destination, scored_destinations[0]["destination_id"])
            else:
                return jsonify(error="No destinations found in catalog."), 404

        origin = str(data.get("origin") or data.get("starting_point") or "").strip()
        result = build_detailed_itinerary(
            dest=selected_dest,
            days=days,
            travelers=travelers,
            budget_per_person=budget,
            interests=interests_set,
            recommended_destinations=recommended_destinations,
            origin=origin,
        )
        return jsonify(result)

    @app.get("/api/itineraries")
    @jwt_required()
    @customer_required
    def get_my_itineraries():
        user_id = int(get_jwt_identity())
        rows = SavedItinerary.query.filter_by(user_id=user_id).order_by(SavedItinerary.created_at.desc()).all()
        return jsonify([saved_itinerary_json(row) for row in rows])

    @app.post("/api/itineraries")
    @jwt_required()
    @customer_required
    def save_itinerary():
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        try:
            destination_id = int(data.get("destination_id"))
            days = int(data.get("days", 1))
            travelers = int(data.get("travelers", 1))
            budget_per_person = Decimal(str(data.get("budget_per_person", 0)))
            total_budget = Decimal(str(data.get("total_budget", budget_per_person * travelers)))
            estimated_accommodation = Decimal(str(data.get("estimated_accommodation", 0)))
            estimated_transport = Decimal(str(data.get("estimated_transport", 0)))
            estimated_food = Decimal(str(data.get("estimated_food", 0)))
            estimated_sightseeing = Decimal(str(data.get("estimated_sightseeing", 0)))
            total_estimated_cost = Decimal(str(data.get("total_estimated_cost", 0)))
            cost_per_person = Decimal(str(data.get("cost_per_person", 0)))
            remaining_budget = Decimal(str(data.get("remaining_budget", 0)))
            within_budget = bool(data.get("within_budget", True))
            itinerary_data = data.get("itinerary_data")
            if not isinstance(itinerary_data, (dict, list)):
                return jsonify(error="Valid itinerary schedule data is required."), 400
        except (InvalidOperation, TypeError, ValueError):
            return jsonify(error="Invalid itinerary numerical values."), 400

        title = str(data.get("title", "")).strip()
        destination = db.session.get(Destination, destination_id)
        if not destination:
            return jsonify(error="Destination not found."), 404
        if not title:
            title = f"{days}-Day {destination.name} Discovery"

        row = SavedItinerary(
            user_id=user_id,
            destination_id=destination_id,
            title=title,
            days=days,
            travelers=travelers,
            budget_per_person=budget_per_person,
            total_budget=total_budget,
            estimated_accommodation=estimated_accommodation,
            estimated_transport=estimated_transport,
            estimated_food=estimated_food,
            estimated_sightseeing=estimated_sightseeing,
            total_estimated_cost=total_estimated_cost,
            cost_per_person=cost_per_person,
            remaining_budget=remaining_budget,
            within_budget=within_budget,
            itinerary_data=itinerary_data,
            generation_mode=data.get("generation_mode", "rule_based"),
        )
        db.session.add(row)
        db.session.commit()
        return jsonify(itinerary=saved_itinerary_json(row)), 201

    @app.get("/api/itineraries/<int:itinerary_id>")
    @jwt_required()
    @customer_required
    def get_itinerary_detail(itinerary_id: int):
        user_id = int(get_jwt_identity())
        row = SavedItinerary.query.filter_by(id=itinerary_id, user_id=user_id).first()
        if not row:
            return jsonify(error="Itinerary not found."), 404
        return jsonify(saved_itinerary_json(row))

    @app.delete("/api/itineraries/<int:itinerary_id>")
    @jwt_required()
    @customer_required
    def delete_saved_itinerary(itinerary_id: int):
        user_id = int(get_jwt_identity())
        row = SavedItinerary.query.filter_by(id=itinerary_id, user_id=user_id).first()
        if not row:
            return jsonify(error="Itinerary not found."), 404
        db.session.delete(row)
        db.session.commit()
        return jsonify(message="Itinerary deleted successfully.")

    @app.put("/api/itineraries/<int:itinerary_id>")
    @jwt_required()
    @customer_required
    def update_saved_itinerary(itinerary_id: int):
        user_id = int(get_jwt_identity())
        row = SavedItinerary.query.filter_by(id=itinerary_id, user_id=user_id).first()
        if not row:
            return jsonify(error="Itinerary not found."), 404
        data = request.get_json(silent=True) or {}
        if "title" in data and str(data["title"]).strip():
            row.title = str(data["title"]).strip()
        db.session.commit()
        return jsonify(itinerary=saved_itinerary_json(row))

    @app.get("/api/bookings")
    @jwt_required()
    @customer_required
    def my_bookings():
        rows = Booking.query.filter_by(user_id=int(get_jwt_identity())).order_by(Booking.created_at.desc()).all()
        return jsonify([booking_json(row) for row in rows])

    @app.post("/api/bookings")
    @jwt_required()
    @customer_required
    def create_booking():
        data = request.get_json(silent=True) or {}
        try:
            destination_id = int(data.get("destination_id"))
            hotel_id = int(data.get("hotel_id"))
            guests = int(data.get("guests"))
            check_in = date.fromisoformat(data.get("check_in", ""))
            check_out = date.fromisoformat(data.get("check_out", ""))
            room_type_id = int(data["room_type_id"]) if data.get("room_type_id") else None
            rooms_count = int(data.get("rooms", 1))
        except (TypeError, ValueError):
            return jsonify(error="Provide valid destination, hotel, guest count, and ISO dates."), 400
        destination = Destination.query.filter_by(id=destination_id, active=True).first()
        hotel = Hotel.query.filter_by(id=hotel_id, destination_id=destination_id).first()
        room_type = db.session.get(RoomType, room_type_id) if room_type_id else None
        nights = (check_out - check_in).days
        if not destination or not hotel or not hotel.active:
            return jsonify(error="Choose an available destination and one of its hotels."), 400
        if nights < 1 or check_in < date.today() or not 1 <= guests <= 20 or not 1 <= rooms_count <= 20:
            return jsonify(error="Choose future dates, 1–20 guests, and 1–20 rooms."), 400
        if not room_type_id:
            return jsonify(error="Choose a room type with listed availability before booking."), 409
        if not room_type or room_type.hotel_id != hotel.id or not room_type.active:
            return jsonify(error="Choose a room type belonging to this hotel."), 400
        if not hotel_room_is_bookable(hotel, room_type):
            return jsonify(error="This room has no valid bookable rate. Contact an administrator for updated pricing."), 409
        if guests > room_type.capacity * rooms_count:
            return jsonify(error="Guest count exceeds the selected rooms' combined capacity."), 400
        inventory = room_type.total_rooms
        if inventory is None:
            inventory = room_type.available_rooms
        if inventory is None or inventory < rooms_count:
            return jsonify(error="Room inventory has not been supplied for these dates."), 409

        # Lock this inventory row before checking reservations so simultaneous requests
        # cannot both claim the final rooms for overlapping dates.
        db.session.execute(
            update(RoomType)
            .where(RoomType.id == room_type.id)
            .values(total_rooms=RoomType.total_rooms)
        )
        if available_rooms_for_stay(room_type, check_in, check_out) < rooms_count:
            db.session.rollback()
            return jsonify(error="The selected room type is not available for those dates."), 409

        nightly_rate = room_type.nightly_rate
        amount = (nightly_rate * nights * rooms_count).quantize(Decimal("0.01"))
        booking = Booking(
            user_id=int(get_jwt_identity()), destination_id=destination_id, hotel_id=hotel_id,
            room_type_id=room_type.id, check_in=check_in, check_out=check_out,
            guests=guests, rooms_count=rooms_count, amount=amount, status="pending",
            is_demo=hotel.is_demo or room_type.price_basis == "estimate",
        )
        db.session.add(booking)
        db.session.flush()
        booking.booking_reference = f"BK-{booking.id:06d}"
        db.session.add(Payment(booking_id=booking.id, amount=amount, status="pending"))
        db.session.commit()
        return jsonify(booking=booking_json(booking)), 201

    @app.patch("/api/bookings/<int:booking_id>")
    @jwt_required()
    @customer_required
    def cancel_booking(booking_id: int):
        booking = Booking.query.filter_by(
            id=booking_id, user_id=int(get_jwt_identity())
        ).first()
        if not booking:
            return jsonify(error="Booking not found."), 404
        if booking.status != "pending":
            return jsonify(error="Only pending bookings can be cancelled."), 409
        booking.status = "cancelled"
        db.session.commit()
        return jsonify(booking=booking_json(booking))

    @app.get("/api/admin/summary")
    @jwt_required()
    @admin_required
    def admin_summary():
        now = datetime.now(timezone.utc)
        months = []
        current_month = now.year * 12 + now.month - 1
        for month_index in range(current_month - 5, current_month + 1):
            year, month_number = divmod(month_index, 12)
            month_start = now.replace(year=year, month=month_number + 1, day=1)
            month_end = month_start.replace(year=year + (month_number == 11), month=(month_number + 1) % 12 + 1)
            bookings_count = Booking.query.filter(Booking.created_at >= month_start, Booking.created_at < month_end).count()
            revenue = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
                Payment.status == "paid", Payment.paid_at >= month_start, Payment.paid_at < month_end
            ).scalar()
            months.append({"month": month_start.strftime("%b %Y"), "bookings": bookings_count, "revenue": float(revenue)})

        popular = db.session.query(
            Destination.id, Destination.name, func.count(Booking.id).label("bookings")
        ).outerjoin(Booking, Booking.destination_id == Destination.id).group_by(
            Destination.id, Destination.name
        ).order_by(func.count(Booking.id).desc(), Destination.name).limit(5).all()
        statuses = {
            status: Booking.query.filter_by(status=status).count()
            for status in ("pending", "confirmed", "cancelled")
        }
        revenue_total = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.status == "paid"
        ).scalar()
        return jsonify(
            users=User.query.filter_by(role="customer").count(),
            bookings=Booking.query.count(),
            booking_statuses=statuses,
            revenue=float(revenue_total),
            monthly=months,
            popular_destinations=[{"id": row.id, "name": row.name, "bookings": row.bookings} for row in popular],
        )

    @app.get("/api/admin/customers")
    @jwt_required()
    @admin_required
    def admin_customers():
        rows = db.session.query(User, func.count(Booking.id)).outerjoin(
            Booking, Booking.user_id == User.id
        ).filter(User.role == "customer").group_by(User.id).order_by(User.created_at.desc()).all()
        return jsonify([
            {"id": user.id, "name": user.name, "email": user.email,
             "created_at": user.created_at.isoformat(), "bookings": bookings}
            for user, bookings in rows
        ])

    @app.get("/api/admin/bookings")
    @jwt_required()
    @admin_required
    def admin_bookings():
        try:
            rows = filtered_bookings()
        except BadRequest as error:
            return jsonify(error=error.description), 400
        return jsonify([booking_json(row, include_customer=True) for row in rows])

    @app.patch("/api/admin/bookings/<int:booking_id>")
    @jwt_required()
    @admin_required
    def update_booking(booking_id: int):
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return jsonify(error="Booking not found."), 404
        data = request.get_json(silent=True) or {}
        status = data.get("status")
        payment_status = data.get("payment_status")
        if status is not None:
            if status not in ("pending", "confirmed", "cancelled"):
                return jsonify(error="Invalid booking status."), 400
            if booking.status == "cancelled" and status != "cancelled" and booking.room_type_id:
                room_type = db.session.get(RoomType, booking.room_type_id)
                if (
                    not room_type
                    or available_rooms_for_stay(room_type, booking.check_in, booking.check_out)
                    < booking.rooms_count
                ):
                    db.session.rollback()
                    return jsonify(error="There are not enough rooms available for this booking's dates."), 409
            booking.status = status
            if status == "confirmed":
                if not booking.payments:
                    db.session.add(Payment(booking_id=booking.id, amount=booking.amount, status="paid", paid_at=datetime.now(timezone.utc)))
                else:
                    for p in booking.payments:
                        p.status = "paid"
                        p.paid_at = datetime.now(timezone.utc)
        if payment_status is not None:
            if payment_status not in ("pending", "paid", "failed", "refunded"):
                return jsonify(error="Invalid payment status."), 400
            payment = booking.payments[0] if booking.payments else Payment(booking_id=booking.id, amount=booking.amount)
            payment.status = payment_status
            payment.paid_at = datetime.now(timezone.utc) if payment_status == "paid" else None
            db.session.add(payment)
        db.session.commit()
        return jsonify(booking=booking_json(booking, include_customer=True))

    @app.get("/api/admin/bookings/export")
    @jwt_required()
    @admin_required
    def export_bookings():
        try:
            bookings = filtered_bookings()
        except BadRequest as error:
            return jsonify(error=error.description), 400
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Bookings"
        headers = [
            "Booking ID", "Customer Name", "Customer Email", "Destination", "Hotel",
            "Check-in Date", "Check-out Date", "Guests", "Booking Amount (INR)",
            "Payment Status", "Booking Status", "Booking Date", "Room Type", "Booking Reference",
        ]
        sheet.append(headers)
        for booking in bookings:
            ref = booking.booking_reference if getattr(booking, "booking_reference", "") else f"BK-{booking.id:06d}"
            sheet.append([
                booking.id, booking.customer.name, booking.customer.email, booking.destination.name, booking.hotel.name,
                booking.check_in, booking.check_out, booking.guests, float(booking.amount),
                booking.payments[0].status if booking.payments else "unpaid", booking.status, booking.created_at.replace(tzinfo=None),
                booking.room_type.name if booking.room_type else "", ref,
            ])
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="0F766E")
        for row in sheet.iter_rows(min_row=2):
            for index in (6, 7):
                row[index - 1].number_format = "dd-mmm-yyyy"
            row[8].number_format = '"₹"#,##0.00'
            row[11].number_format = "dd-mmm-yyyy hh:mm"
        widths = [14, 24, 32, 24, 24, 16, 16, 10, 22, 18, 18, 22, 22]
        for index, width in enumerate(widths, 1):
            sheet.column_dimensions[get_column_letter(index)].width = width
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return send_file(
            output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True, download_name=f"tourism-bookings-{date.today().isoformat()}.xlsx",
        )

    @app.route("/api/admin/destinations", methods=["GET", "POST"])
    @jwt_required()
    @admin_required
    def manage_destinations():
        if request.method == "GET":
            return jsonify([destination_json(row, include_attractions=True) for row in Destination.query.order_by(Destination.name).all()])
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        if not name:
            return jsonify(error="Destination name is required."), 400
        existing = Destination.query.filter(func.lower(Destination.name) == name.casefold()).first()
        if existing:
            return jsonify(error=f"A destination named '{existing.name}' already exists."), 409
        row = Destination(
            name=name,
            state=str(data.get("state", "")).strip(),
            region=str(data.get("region", "")).strip(),
            description=str(data.get("description", "")).strip(),
            image_url=str(data.get("image_url", "")).strip(),
            best_time_to_visit=str(data.get("best_time_to_visit", "")).strip(),
            budget_range=str(data.get("budget_range", "")).strip(),
            active=bool(data.get("active", True)),
        )
        db.session.add(row)
        db.session.commit()
        return jsonify(destination=destination_json(row, include_attractions=True)), 201

    @app.route("/api/admin/destinations/<int:item_id>", methods=["PUT", "DELETE"])
    @jwt_required()
    @admin_required
    def edit_destination(item_id: int):
        row = db.session.get(Destination, item_id)
        if not row:
            return jsonify(error="Destination not found."), 404
        if request.method == "DELETE":
            if not Hotel.query.filter_by(destination_id=row.id).first() and not TouristAttraction.query.filter_by(destination_id=row.id).first():
                db.session.delete(row)
                db.session.commit()
                return jsonify(message="Destination deleted.")
            row.active = False
            db.session.commit()
            return jsonify(destination=destination_json(row, include_attractions=True))
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", row.name)).strip()
        if not name:
            return jsonify(error="Destination name is required."), 400
        dup = Destination.query.filter(func.lower(Destination.name) == name.casefold(), Destination.id != item_id).first()
        if dup:
            return jsonify(error=f"A destination named '{dup.name}' already exists."), 409
        row.name = name
        if "state" in data:
            row.state = str(data["state"]).strip()
        if "region" in data:
            row.region = str(data["region"]).strip()
        if "description" in data:
            row.description = str(data["description"]).strip()
        if "image_url" in data:
            image_url = str(data["image_url"]).strip()
            if image_url and not image_url.startswith(("https://", "http://")):
                return jsonify(error="Destination image URL must use HTTP or HTTPS."), 400
            row.image_url = image_url
        if "best_time_to_visit" in data:
            row.best_time_to_visit = str(data["best_time_to_visit"]).strip()
        if "budget_range" in data:
            row.budget_range = str(data["budget_range"]).strip()
        if "active" in data:
            if not isinstance(data["active"], bool):
                return jsonify(error="Active status must be true or false."), 400
            row.active = data["active"]
        db.session.commit()
        return jsonify(destination=destination_json(row, include_attractions=True))

    @app.route("/api/admin/hotels", methods=["GET", "POST"])
    @jwt_required()
    @admin_required
    def manage_hotels():
        if request.method == "GET":
            results = []
            query = Hotel.query
            if request.args.get("include_archived") != "true":
                query = query.filter(Hotel.active.is_(True))
            for row in query.order_by(Hotel.name).all():
                hotel_data = hotel_json(row)
                hotel_data["rooms"] = [
                    room_type_json(room)
                    for room in sorted(row.rooms, key=lambda item: item.nightly_rate)
                ]
                results.append(hotel_data)
            return jsonify(results)
        data = request.get_json(silent=True) or {}
        try:
            destination_id = int(data.get("destination_id"))
            rate = Decimal(str(data.get("nightly_rate", "")))
            rating = float(data.get("rating"))
        except (ValueError, TypeError, InvalidOperation):
            return jsonify(error="Provide a destination, nightly rate, and rating."), 400
        name = str(data.get("name", "")).strip()
        destination = db.session.get(Destination, destination_id)
        if (
            not name or len(name) > 160 or not rate.is_finite() or rate <= 0
            or not destination or not destination.active
            or not 0 <= rating <= 5
        ):
            return jsonify(error="Enter a hotel name, positive nightly rate, active destination, and rating from 0 to 5."), 400

        address = str(data.get("address", "")).strip()
        description = str(data.get("description", "")).strip()
        image_url = str(data.get("image_url", "")).strip()
        source_url = str(data.get("source_url", "")).strip()
        check_in_policy = str(data.get("check_in_policy", "14:00")).strip() or "14:00"
        check_out_policy = str(data.get("check_out_policy", "11:00")).strip() or "11:00"
        is_demo = bool(data.get("is_demo", False))
        price_basis = str(data.get("price_basis", "estimate" if is_demo else "unverified")).strip().lower()
        if price_basis not in ("unverified", "estimate", "verified", "unavailable"):
            price_basis = "estimate" if is_demo else "unverified"
        if price_basis == "verified" and not source_url.startswith("https://"):
            return jsonify(error="A verified hotel rate requires its HTTPS official source URL."), 400

        facilities = data.get("facilities", [])
        if isinstance(facilities, str):
            facilities = [item.strip() for item in facilities.split(",") if item.strip()]
        if not isinstance(facilities, list) or any(not isinstance(item, str) for item in facilities):
            facilities = []

        google_maps_url = str(data.get("google_maps_url", "")).strip()
        latitude = None
        longitude = None
        if data.get("latitude") not in (None, ""):
            try:
                latitude = float(data["latitude"])
            except (ValueError, TypeError):
                pass
        if data.get("longitude") not in (None, ""):
            try:
                longitude = float(data["longitude"])
            except (ValueError, TypeError):
                pass

        row = Hotel(
            destination_id=destination_id,
            name=name,
            nightly_rate=rate,
            price_basis=price_basis,
            is_demo=is_demo,
            source_url=source_url,
            address=address,
            google_maps_url=google_maps_url,
            latitude=latitude,
            longitude=longitude,
            image_url=image_url,
            description=description,
            check_in_policy=check_in_policy,
            check_out_policy=check_out_policy,
        )
        db.session.add(row)
        row.profile = HotelProfile(rating=rating, rating_verified=price_basis == "verified", facilities=facilities)
        db.session.commit()
        return jsonify(hotel=hotel_json(row)), 201

    @app.route("/api/admin/hotels/<int:item_id>", methods=["PUT", "DELETE"])
    @jwt_required()
    @admin_required
    def edit_hotel(item_id: int):
        row = db.session.get(Hotel, item_id)
        if not row:
            return jsonify(error="Hotel not found."), 404
        if request.method == "DELETE":
            if not Booking.query.filter_by(hotel_id=row.id).first():
                db.session.delete(row)
                db.session.commit()
                return jsonify(message="Hotel deleted.")
            row.active = False
        else:
            data = request.get_json(silent=True) or {}
            name = str(data.get("name", row.name)).strip()
            if not name:
                return jsonify(error="Hotel name is required."), 400
            row.name = name
            source_url = str(data.get("source_url", row.source_url)).strip()
            if source_url and not source_url.startswith("https://"):
                return jsonify(error="Hotel source must use HTTPS."), 400
            price_basis = str(data.get("price_basis", row.price_basis)).strip().lower()
            if price_basis not in ("unverified", "estimate", "verified", "unavailable"):
                return jsonify(error="Choose unverified, estimated, verified, or unavailable pricing."), 400
            if price_basis == "verified" and not source_url.startswith("https://"):
                return jsonify(error="A verified hotel rate requires its HTTPS source URL."), 400
            if "nightly_rate" in data:
                try:
                    rate = Decimal(str(data["nightly_rate"]))
                except (InvalidOperation, ValueError):
                    return jsonify(error="Invalid nightly rate."), 400
                if not rate.is_finite() or rate < 0:
                    return jsonify(error="Nightly rate must be zero or greater."), 400
                row.nightly_rate = rate
                if rate == 0:
                    price_basis = "unavailable"
            row.price_basis = price_basis
            row.source_url = source_url
            if "address" in data:
                row.address = str(data["address"]).strip()
            if "google_maps_url" in data:
                row.google_maps_url = str(data["google_maps_url"]).strip()
            if "latitude" in data:
                val = data["latitude"]
                try:
                    row.latitude = float(val) if val not in (None, "") else None
                except (ValueError, TypeError):
                    pass
            if "longitude" in data:
                val = data["longitude"]
                try:
                    row.longitude = float(val) if val not in (None, "") else None
                except (ValueError, TypeError):
                    pass
            if "description" in data:
                row.description = str(data["description"]).strip()
            if "check_in_policy" in data:
                row.check_in_policy = str(data["check_in_policy"]).strip()
            if "check_out_policy" in data:
                row.check_out_policy = str(data["check_out_policy"]).strip()
            if "is_demo" in data:
                row.is_demo = bool(data["is_demo"])
            if "image_url" in data:
                image_url = str(data["image_url"]).strip()
                if image_url and not image_url.startswith(("https://", "http://")):
                    return jsonify(error="Hotel image URL must use HTTP or HTTPS."), 400
                row.image_url = image_url
            if "price_tier" in data:
                price_tier = str(data["price_tier"]).strip().lower()
                if price_tier not in ("budget", "mid-range", "luxury", "unclassified"):
                    return jsonify(error="Choose budget, mid-range, luxury, or unclassified hotel tier."), 400
                row.price_tier = price_tier
            if "active" in data:
                if not isinstance(data["active"], bool):
                    return jsonify(error="Active status must be true or false."), 400
                row.active = data["active"]
            if "destination_id" in data:
                destination = db.session.get(Destination, data["destination_id"])
                if not destination or not destination.active:
                    return jsonify(error="Destination not found."), 400
                row.destination_id = destination.id
            if "rating" in data or "facilities" in data:
                profile = row.profile or HotelProfile(hotel_id=row.id, facilities=[])
                if "rating" in data:
                    try:
                        profile.rating = float(data["rating"]) if data["rating"] not in (None, "") else None
                    except (TypeError, ValueError):
                        return jsonify(error="Rating must be between 0 and 5."), 400
                    if profile.rating is not None and not 0 <= profile.rating <= 5:
                        return jsonify(error="Rating must be between 0 and 5."), 400
                if "facilities" in data:
                    facilities = data["facilities"]
                    if isinstance(facilities, str):
                        facilities = [item.strip() for item in facilities.split(",") if item.strip()]
                    if not isinstance(facilities, list) or any(not isinstance(item, str) for item in facilities):
                        return jsonify(error="Facilities must be a list or comma-separated text."), 400
                    profile.facilities = [item.strip() for item in facilities if item.strip()]
                db.session.add(profile)
        db.session.commit()
        return jsonify(hotel=hotel_json(row))

    @app.post("/api/admin/hotels/<int:hotel_id>/rooms")
    @jwt_required()
    @admin_required
    def add_hotel_room(hotel_id: int):
        hotel = db.session.get(Hotel, hotel_id)
        if not hotel or not hotel.active:
            return jsonify(error="Active hotel not found."), 404
        data = request.get_json(silent=True) or {}
        try:
            rate = Decimal(str(data.get("nightly_rate", "") or "0"))
            capacity = int(data.get("capacity", 2))
            available_rooms = data.get("available_rooms")
            available_rooms = int(available_rooms) if available_rooms not in (None, "") else None
        except (InvalidOperation, TypeError, ValueError):
            return jsonify(error="Enter a valid room rate, capacity, and available room count."), 400
        name = str(data.get("name", "")).strip()
        price_basis = str(data.get("price_basis", "unverified")).strip().lower()
        if price_basis not in ("unverified", "estimate", "verified", "unavailable"):
            return jsonify(error="Choose unavailable, unverified, estimated, or verified room pricing."), 400
        if price_basis == "verified" and not hotel.source_url.startswith("https://"):
            return jsonify(error="A verified room rate requires the hotel's HTTPS source URL."), 400
        if not name or not rate.is_finite() or rate < 0 or not 1 <= capacity <= 20:
            return jsonify(error="Room name/rate are required and capacity must be 1–20."), 400
        if rate == 0:
            price_basis = "unavailable"
        if available_rooms is not None and not 0 <= available_rooms <= 10000:
            return jsonify(error="Available rooms must be between 0 and 10,000."), 400
        room = RoomType(
            hotel_id=hotel.id, name=name, nightly_rate=rate, capacity=capacity,
            available_rooms=available_rooms, total_rooms=available_rooms,
            price_basis=price_basis,
        )
        db.session.add(room)
        db.session.commit()
        return jsonify(room_type=room_type_json(room)), 201

    @app.route("/api/admin/rooms/<int:room_id>", methods=["PUT", "DELETE"])
    @jwt_required()
    @admin_required
    def edit_hotel_room(room_id: int):
        room = db.session.get(RoomType, room_id)
        if not room:
            return jsonify(error="Hotel room type not found."), 404
        if request.method == "DELETE":
            room.active = False
            db.session.commit()
            return jsonify(room_type=room_type_json(room))

        data = request.get_json(silent=True) or {}
        name = str(data.get("name", room.name)).strip()
        price_basis = str(data.get("price_basis", room.price_basis)).strip().lower()
        if price_basis not in ("unverified", "estimate", "verified", "unavailable"):
            return jsonify(error="Choose unavailable, unverified, estimated, or verified room pricing."), 400
        try:
            rate = Decimal(str(data.get("nightly_rate", room.nightly_rate) or "0"))
            capacity = int(data.get("capacity", room.capacity))
            available_value = data.get("available_rooms", room.available_rooms)
            available_rooms = int(available_value) if available_value not in (None, "") else None
        except (InvalidOperation, TypeError, ValueError):
            return jsonify(error="Enter a valid room rate, capacity, and available room count."), 400
        if not name or not rate.is_finite() or rate < 0 or not 1 <= capacity <= 20:
            return jsonify(error="Room name/rate are required and capacity must be 1–20."), 400
        if available_rooms is not None and not 0 <= available_rooms <= 10000:
            return jsonify(error="Available rooms must be between 0 and 10,000."), 400
        if price_basis == "verified" and not room.hotel.source_url.startswith("https://"):
            return jsonify(error="A verified room rate requires the hotel's HTTPS source URL."), 400
        if rate == 0:
            price_basis = "unavailable"

        room.name = name
        room.nightly_rate = rate
        room.capacity = capacity
        room.available_rooms = available_rooms
        room.total_rooms = available_rooms
        room.price_basis = price_basis
        if "active" in data:
            if not isinstance(data["active"], bool):
                return jsonify(error="Active status must be true or false."), 400
            room.active = data["active"]
        db.session.commit()
        return jsonify(room_type=room_type_json(room))

    @app.get("/api/admin/transport/services")
    @jwt_required()
    @admin_required
    def admin_transport_services():
        return jsonify([
            transport_service_json(row)
            for row in TransportService.query.order_by(TransportService.id.desc()).all()
        ])

    @app.post("/api/admin/transport/services")
    @jwt_required()
    @admin_required
    def add_transport_service():
        data = request.get_json(silent=True) or {}
        try:
            date_str = str(data.get("service_date", "")).strip()
            service_date = date.fromisoformat(date_str) if date_str else date.today()
            fare = Decimal(str(data.get("ticket_price", "")))
            seats_value = data.get("available_seats")
            seats = int(seats_value) if seats_value not in (None, "") else None
            destination_id = int(data["destination_id"]) if data.get("destination_id") else None
        except (InvalidOperation, TypeError, ValueError):
            return jsonify(error="Provide a valid service date, fare, and optional seat count."), 400
        mode = str(data.get("mode") or data.get("category") or "").strip().lower()
        origin = str(data.get("origin", "")).strip()
        destination = str(data.get("destination", "")).strip()
        operator = str(data.get("operator", "")).strip()
        departure = str(data.get("departure_time", "")).strip()
        arrival = str(data.get("arrival_time", "")).strip()
        booking_url = str(data.get("booking_url") or data.get("source_url") or "").strip()
        source_url = booking_url
        price_basis = str(data.get("price_basis", "estimate")).strip().lower()
        availability_verified = data.get("availability_verified") in (True, "true", "on", "1", 1)
        destination_row = db.session.get(Destination, destination_id) if destination_id else None
        if mode not in ("bus", "train"):
            return jsonify(error="Transport options are restricted to bus and train only. Taxi services have been discontinued."), 400
        if not all((origin, destination, operator, departure, arrival)) or len(origin) > 160 or len(destination) > 160:
            return jsonify(error="Origin, destination, operator, and travel times are required."), 400
        if destination_id and (not destination_row or not destination_row.active):
            return jsonify(error="Choose an active destination for this service."), 400
        if price_basis not in ("estimate", "verified", "unverified", "sample"):
            return jsonify(error="Choose estimated, verified, sample, or unverified pricing."), 400
        if price_basis == "verified" and not source_url.startswith("https://"):
            return jsonify(error="A verified fare requires its HTTPS source URL."), 400
        if availability_verified and (seats is None or not source_url.startswith("https://")):
            return jsonify(error="Verified availability requires a seat count and its HTTPS source URL."), 400
        if not fare.is_finite() or fare < 0 or fare > Decimal("10000000"):
            return jsonify(error="Fare must be between ₹0 and ₹10,000,000."), 400
        if seats is not None and not 0 <= seats <= 10000:
            return jsonify(error="Available seats must be between 0 and 10,000."), 400
        if mode in ("bus", "train") and seats is None and availability_verified:
            return jsonify(error="Enter a seat count before listing a verified bookable bus/train service."), 400

        service_name = str(data.get("service_name", "")).strip()
        # Avoid duplicate transport records
        duplicate = TransportService.query.filter(
            TransportService.active.is_(True),
            TransportService.mode == mode,
            func.lower(TransportService.operator) == operator.lower(),
            func.lower(TransportService.origin) == origin.lower(),
            func.lower(TransportService.destination) == destination.lower(),
            TransportService.departure_time == departure,
            func.lower(TransportService.service_name) == service_name.lower(),
        ).first()
        if duplicate:
            return jsonify(error="A transport service with this operator, route, service name, and departure time already exists."), 409

        class_fares = data.get("class_fares")
        if not isinstance(class_fares, dict):
            class_fares = {}

        boarding_point = str(data.get("boarding_point", "")).strip()
        dropping_point = str(data.get("dropping_point", "")).strip()
        booking_status = str(data.get("booking_status", "Available")).strip()

        service = TransportService(
            destination_id=destination_id,
            mode=mode, origin=origin, destination=destination, operator=operator,
            service_name=service_name,
            service_type=str(data.get("service_type", "")).strip(),
            departure_time=departure, arrival_time=arrival,
            duration=str(data.get("duration", "")).strip(),
            distance_km=str(data.get("distance_km", "")).strip(),
            origin_station=str(data.get("origin_station", "")).strip(),
            destination_station=str(data.get("destination_station", "")).strip(),
            boarding_point=boarding_point,
            dropping_point=dropping_point,
            booking_status=booking_status,
            available_classes=str(data.get("available_classes", "")).strip(),
            class_fares=class_fares,
            pricing_unit=str(data.get("pricing_unit", "per_person")).strip(),
            contact_number=str(data.get("contact_number", "")).strip(),
            booking_url=booking_url,
            is_daily=data.get("is_daily") in (True, "true", "1", 1, None),
            service_date=service_date,
            ticket_price=fare, available_seats=seats, availability_verified=availability_verified,
            source_url=source_url, price_basis=price_basis,
            availability_updated_at=datetime.now(timezone.utc),
            active=True,
        )
        db.session.add(service)
        db.session.commit()
        return jsonify(service=transport_service_json(service)), 201

    @app.put("/api/admin/transport/services/<int:service_id>")
    @app.patch("/api/admin/transport/services/<int:service_id>")
    @jwt_required()
    @admin_required
    def edit_transport_service(service_id: int):
        service = db.session.get(TransportService, service_id)
        if not service:
            return jsonify(error="Transport service not found."), 404
        data = request.get_json(silent=True) or {}

        if "mode" in data or "category" in data:
            mode = str(data.get("mode") or data.get("category")).strip().lower()
            if mode not in ("bus", "train"):
                return jsonify(error="Transport options are restricted to bus and train only."), 400
            service.mode = mode
        if "origin" in data:
            orig = str(data["origin"]).strip()
            if not orig or len(orig) > 160:
                return jsonify(error="Origin cannot be empty or exceed 160 characters."), 400
            service.origin = orig
        if "destination" in data:
            dest = str(data["destination"]).strip()
            if not dest or len(dest) > 160:
                return jsonify(error="Destination cannot be empty or exceed 160 characters."), 400
            service.destination = dest
        if "operator" in data:
            service.operator = str(data["operator"]).strip()
        if "service_name" in data:
            service.service_name = str(data["service_name"]).strip()
        if "service_type" in data:
            service.service_type = str(data["service_type"]).strip()
        if "departure_time" in data:
            service.departure_time = str(data["departure_time"]).strip()
        if "arrival_time" in data:
            service.arrival_time = str(data["arrival_time"]).strip()
        if "duration" in data:
            service.duration = str(data["duration"]).strip()
        if "distance_km" in data:
            service.distance_km = str(data["distance_km"]).strip()
        if "origin_station" in data:
            service.origin_station = str(data["origin_station"]).strip()
        if "destination_station" in data:
            service.destination_station = str(data["destination_station"]).strip()
        if "boarding_point" in data:
            service.boarding_point = str(data["boarding_point"]).strip()
        if "dropping_point" in data:
            service.dropping_point = str(data["dropping_point"]).strip()
        if "booking_status" in data:
            service.booking_status = str(data["booking_status"]).strip()
        if "available_classes" in data:
            service.available_classes = str(data["available_classes"]).strip()
        if "class_fares" in data and isinstance(data["class_fares"], dict):
            service.class_fares = data["class_fares"]
        if "pricing_unit" in data:
            service.pricing_unit = str(data["pricing_unit"]).strip()
        if "contact_number" in data:
            service.contact_number = str(data["contact_number"]).strip()
        if "booking_url" in data or "source_url" in data:
            url_val = str(data.get("booking_url") or data.get("source_url") or "").strip()
            service.booking_url = url_val
            service.source_url = url_val
        if "is_daily" in data:
            service.is_daily = data["is_daily"] in (True, "true", "1", 1)
        if "service_date" in data and data["service_date"]:
            try:
                service.service_date = date.fromisoformat(str(data["service_date"]))
            except ValueError:
                return jsonify(error="Invalid date format YYYY-MM-DD."), 400
        if "ticket_price" in data:
            try:
                fare = Decimal(str(data["ticket_price"]))
                if fare < 0:
                    return jsonify(error="Fare must be positive."), 400
                service.ticket_price = fare
            except (InvalidOperation, ValueError):
                return jsonify(error="Invalid fare value."), 400
        if "available_seats" in data:
            seats_val = data["available_seats"]
            service.available_seats = int(seats_val) if seats_val not in (None, "") else None
        if "availability_verified" in data:
            service.availability_verified = data["availability_verified"] in (True, "true", "1", 1)
        if "price_basis" in data:
            pb = str(data["price_basis"]).strip().lower()
            if pb in ("verified", "estimate", "unverified", "sample"):
                service.price_basis = pb
        if "active" in data:
            service.active = data["active"] in (True, "true", "1", 1)
        if "destination_id" in data:
            dest_id = data["destination_id"]
            service.destination_id = int(dest_id) if dest_id not in (None, "") else None

        service.availability_updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify(service=transport_service_json(service)), 200

    @app.post("/api/admin/transport/services/<int:service_id>/restore")
    @jwt_required()
    @admin_required
    def restore_transport_service(service_id: int):
        service = db.session.get(TransportService, service_id)
        if not service:
            return jsonify(error="Transport service not found."), 404
        service.active = True
        db.session.commit()
        return jsonify(message="Transport service restored to active status.", service=transport_service_json(service))

    @app.post("/api/admin/transport/seed")
    @jwt_required()
    @admin_required
    def seed_transport_catalog_endpoint():
        from seed_data import seed_transport_catalog
        try:
            counts = seed_transport_catalog(db)
            return jsonify(
                message="Transport catalog seeded successfully with verified-style and estimated routes.",
                counts=counts,
            )
        except Exception as error:
            db.session.rollback()
            app.logger.exception("Transport catalog seeding failed")
            return jsonify(error=f"Seeding failed: {error}"), 500

    @app.get("/api/admin/transport/reservations")
    @jwt_required()
    @admin_required
    def admin_transport_reservations():
        rows = TransportReservation.query.order_by(TransportReservation.created_at.desc()).all()
        return jsonify([
            {**transport_reservation_json(row), "customer_name": row.user.name, "customer_email": row.user.email}
            for row in rows
        ])

    @app.post("/api/admin/catalog/seed-demo-data")
    @jwt_required()
    @admin_required
    def seed_demo_catalog_api():
        from seed_data import seed_verified_catalog, seed_demo_hotels_and_rooms

        try:
            dest_counts = seed_verified_catalog(db)
            hotel_counts = seed_demo_hotels_and_rooms(db)
        except Exception:
            db.session.rollback()
            app.logger.exception("Demonstration catalog refresh failed")
            return jsonify(error="The demonstration hotel catalog could not be refreshed. Check server logs."), 500
        return jsonify(
            message="Demonstration hotels, room types, and destinations seeded successfully.",
            destinations=dest_counts,
            hotels=hotel_counts,
        )

    @app.post("/api/admin/catalog/seed-real-data")
    @jwt_required()
    @admin_required
    def seed_catalog_api():
        from seed_data import seed_verified_catalog

        try:
            counts = seed_verified_catalog(db)
        except Exception:
            db.session.rollback()
            app.logger.exception("Source-linked catalog refresh failed")
            return jsonify(error="The destination catalog could not be refreshed. Check the server log for details."), 500
        return jsonify(
            message="Destination records refreshed. Hotel and place records are managed by administrators and were not added.",
            updated=counts,
        )

    @app.delete("/api/admin/transport/services/<int:service_id>")
    @jwt_required()
    @admin_required
    def archive_transport_service(service_id: int):
        service = db.session.get(TransportService, service_id)
        if not service:
            return jsonify(error="Transport service not found."), 404
        service.active = False
        db.session.commit()
        return jsonify(message="Transport service archived.")

    @app.get("/api/admin/attractions")
    @jwt_required()
    @admin_required
    def admin_attractions():
        return jsonify([
            attraction_json(row)
            for row in TouristAttraction.query.order_by(TouristAttraction.name).all()
        ])

    @app.post("/api/admin/attractions")
    @jwt_required()
    @admin_required
    def add_attraction():
        data = request.get_json(silent=True) or {}
        try:
            destination_id = int(data.get("destination_id"))
            entry_fee = Decimal(str(data.get("entry_fee", data.get("estimated_cost", 0)) or 0))
            duration = float(data.get("duration_hours", 2) or 2)
        except (InvalidOperation, TypeError, ValueError):
            return jsonify(error="Provide a destination and valid activity cost/duration."), 400
        destination = Destination.query.filter_by(id=destination_id).first()
        name = str(data.get("name", "")).strip()
        if not destination or not name:
            return jsonify(error="Choose a destination and provide a place name."), 400
        interests = data.get("interests", [])
        if isinstance(interests, str):
            interests = [item.strip() for item in interests.split(",") if item.strip()]
        if not isinstance(interests, list) or any(not isinstance(item, str) for item in interests):
            return jsonify(error="Interests must be a list or comma-separated text."), 400
        if not entry_fee.is_finite() or entry_fee < 0 or not 0.25 <= duration <= 24:
            return jsonify(error="Activity cost must be non-negative and duration must be 0.25–24 hours."), 400
        source_url = str(data.get("source_url", "")).strip()
        if source_url and not source_url.startswith(("https://", "http://")):
            return jsonify(error="Attraction source must use HTTP or HTTPS."), 400
        cost_basis = str(data.get("cost_basis", "free" if entry_fee == 0 else "verified")).strip().lower()
        lat = data.get("latitude")
        lng = data.get("longitude")
        lat_val = float(lat) if lat not in (None, "") else None
        lng_val = float(lng) if lng not in (None, "") else None

        attraction = TouristAttraction(
            destination_id=destination.id,
            name=name,
            description=str(data.get("description", "")).strip(),
            category=str(data.get("category", "Sightseeing")).strip() or "Sightseeing",
            interests=[item.strip() for item in interests if item.strip()],
            image_url=str(data.get("image_url", "")).strip(),
            duration_hours=duration,
            opening_hours=str(data.get("opening_hours", "")).strip(),
            entry_fee=entry_fee,
            estimated_cost=entry_fee,
            latitude=lat_val,
            longitude=lng_val,
            best_time_to_visit=str(data.get("best_time_to_visit", "")).strip(),
            verification_status=str(data.get("verification_status", "verified")).strip(),
            cost_basis=cost_basis,
            source_url=source_url,
            active=True,
        )
        db.session.add(attraction)
        db.session.commit()
        return jsonify(attraction=attraction_json(attraction)), 201

    @app.route("/api/admin/attractions/<int:item_id>", methods=["PUT", "DELETE"])
    @jwt_required()
    @admin_required
    def edit_attraction(item_id: int):
        attraction = db.session.get(TouristAttraction, item_id)
        if not attraction:
            return jsonify(error="Place not found."), 404
        if request.method == "DELETE":
            db.session.delete(attraction)
            db.session.commit()
            return jsonify(message="Place deleted.")
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", attraction.name)).strip()
        if not name:
            return jsonify(error="Place name is required."), 400
        attraction.name = name
        if "destination_id" in data:
            dest_id = int(data["destination_id"])
            if not Destination.query.filter_by(id=dest_id).first():
                return jsonify(error="Selected destination does not exist."), 400
            attraction.destination_id = dest_id
        if "description" in data:
            attraction.description = str(data["description"]).strip()
        if "category" in data:
            attraction.category = str(data["category"]).strip()
        if "image_url" in data:
            attraction.image_url = str(data["image_url"]).strip()
        if "duration_hours" in data:
            try: attraction.duration_hours = float(data["duration_hours"])
            except (ValueError, TypeError): pass
        if "opening_hours" in data:
            attraction.opening_hours = str(data["opening_hours"]).strip()
        if "entry_fee" in data or "estimated_cost" in data:
            fee_val = data.get("entry_fee", data.get("estimated_cost"))
            try:
                fee = Decimal(str(fee_val))
                attraction.entry_fee = fee
                attraction.estimated_cost = fee
                attraction.cost_basis = "free" if fee == 0 else "verified"
            except (InvalidOperation, ValueError, TypeError): pass
        if "latitude" in data:
            try: attraction.latitude = float(data["latitude"]) if data["latitude"] not in (None, "") else None
            except (ValueError, TypeError): pass
        if "longitude" in data:
            try: attraction.longitude = float(data["longitude"]) if data["longitude"] not in (None, "") else None
            except (ValueError, TypeError): pass
        if "best_time_to_visit" in data:
            attraction.best_time_to_visit = str(data["best_time_to_visit"]).strip()
        if "verification_status" in data:
            attraction.verification_status = str(data["verification_status"]).strip()
        if "source_url" in data:
            attraction.source_url = str(data["source_url"]).strip()
        if "active" in data:
            attraction.active = bool(data["active"])
        db.session.commit()
        return jsonify(attraction=attraction_json(attraction))

    @app.cli.command("init-db")
    def init_db_command():
        """Create missing application tables without dropping existing data."""
        upgrade_database_schema()
        click.echo("Database tables are ready.")

    @app.cli.command("upgrade-db")
    def upgrade_db_command():
        """Create new travel-planning tables and add nullable fields to existing tables."""
        upgrade_database_schema()
        click.echo("Database schema is up to date; existing records were preserved.")

    @app.cli.command("seed-real-catalog")
    @app.cli.command("seed-demo-data")
    def seed_demo_data_command():
        """Refresh destination records without adding hotels or places."""
        from seed_data import seed_verified_catalog

        try:
            counts = seed_verified_catalog(db)
        except Exception as error:
            db.session.rollback()
            app.logger.exception("Destination catalog refresh failed")
            raise click.ClickException(f"Destination catalog refresh failed: {error}") from error
        click.echo("Destination catalog refreshed; hotel and place records were not added:")
        for record_type, count in counts.items():
            click.echo(f"  {record_type}: {count}")

    @app.cli.command("seed-destinations-places")
    def seed_destinations_places_command():
        """Seed all 15 Indian destinations and 60+ verified tourist attractions."""
        from seed_data import seed_destinations_and_attractions

        upgrade_database_schema()
        counts = seed_destinations_and_attractions(db)
        click.echo("Destinations and attractions seeded successfully:")
        for record_type, count in counts.items():
            click.echo(f"  {record_type}: {count}")

    @app.cli.command("seed-transport-catalog")
    def seed_transport_catalog_command():
        """Seed verified-style and estimated transport routes for bus, train, and taxi."""
        from seed_data import seed_transport_catalog

        upgrade_database_schema()
        try:
            counts = seed_transport_catalog(db)
        except Exception as error:
            db.session.rollback()
            app.logger.exception("Transport catalog seeding failed")
            raise click.ClickException(f"Transport catalog seeding failed: {error}") from error
        click.echo("Transport catalog seeded successfully:")
        for record_type, count in counts.items():
            click.echo(f"  {record_type}: {count}")

    @app.cli.command("clear-hotel-place-catalog")
    def clear_hotel_place_catalog_command():
        """Remove unbooked hotel/place records while preserving booking history."""
        from seed_data import clear_hotel_place_catalog

        try:
            counts = clear_hotel_place_catalog(db)
        except Exception as error:
            db.session.rollback()
            app.logger.exception("Hotel/place catalog cleanup failed")
            raise click.ClickException(f"Hotel/place catalog cleanup failed: {error}") from error
        click.echo("Hotel/place catalog cleanup complete; existing bookings were preserved:")
        for record_type, count in counts.items():
            click.echo(f"  {record_type}: {count}")

    @app.cli.command("create-admin")
    def create_admin_command():
        """Interactively create a privileged administrator account."""
        from getpass import getpass

        email = click.prompt("Admin email").strip().lower()
        name = click.prompt("Admin name").strip()
        password = getpass("Admin password (minimum 14 characters): ")
        if not valid_email(email) or len(password) < 14 or not name:
            raise click.ClickException("Enter a valid email, name, and password of at least 14 characters.")
        if User.query.filter_by(email=email).first():
            raise click.ClickException("That email is already registered.")
        db.session.add(User(name=name, email=email, password_hash=generate_password_hash(password), role="admin"))
        db.session.commit()
        click.echo("Admin account created.")

    return app


def customer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if get_jwt().get("role") != "customer":
            return jsonify(error="Customer access required."), 403
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = get_jwt_identity()
        try:
            user = db.session.get(User, int(user_id)) if user_id else None
        except Exception:
            user = None
        if not user or user.role != "admin":
            return jsonify(error="Administrator access required."), 403
        return view(*args, **kwargs)
    return wrapped


def valid_email(email: str) -> bool:
    return len(email) <= 255 and "@" in email and "." in email.rsplit("@", 1)[-1]


def valid_password(password) -> bool:
    return isinstance(password, str) and len(password) >= 10


def upgrade_database_schema():
    from sqlalchemy import inspect, text

    db.create_all()
    additions = {
        "destination": {
            "state": "VARCHAR(120) NOT NULL DEFAULT ''",
            "best_time_to_visit": "VARCHAR(160) NOT NULL DEFAULT ''",
            "budget_range": "VARCHAR(100) NOT NULL DEFAULT ''",
        },
        "booking": {
            "room_type_id": "INTEGER REFERENCES room_type (id)",
            "rooms_count": "INTEGER NOT NULL DEFAULT 1",
            "is_demo": "BOOLEAN NOT NULL DEFAULT FALSE",
            "booking_reference": "VARCHAR(40) NOT NULL DEFAULT ''",
        },
        "hotel": {
            "price_tier": "VARCHAR(20) NOT NULL DEFAULT 'unclassified'",
            "price_basis": "VARCHAR(20) NOT NULL DEFAULT 'unverified'",
            "is_demo": "BOOLEAN NOT NULL DEFAULT FALSE",
            "source_url": "TEXT NOT NULL DEFAULT ''",
            "address": "TEXT NOT NULL DEFAULT ''",
            "google_maps_url": "TEXT NOT NULL DEFAULT ''",
            "latitude": "FLOAT",
            "longitude": "FLOAT",
            "image_url": "TEXT NOT NULL DEFAULT ''",
            "description": "TEXT NOT NULL DEFAULT ''",
            "check_in_policy": "VARCHAR(160) NOT NULL DEFAULT '14:00'",
            "check_out_policy": "VARCHAR(160) NOT NULL DEFAULT '11:00'",
        },
        "hotel_profile": {"rating_verified": "BOOLEAN NOT NULL DEFAULT FALSE"},
        "room_type": {
            "price_basis": "VARCHAR(20) NOT NULL DEFAULT 'unverified'",
            "active": "BOOLEAN NOT NULL DEFAULT TRUE",
            "total_rooms": "INTEGER",
        },
        "tourist_attraction": {
            "image_url": "TEXT NOT NULL DEFAULT ''",
            "opening_hours": "VARCHAR(160) NOT NULL DEFAULT ''",
            "entry_fee": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "latitude": "FLOAT",
            "longitude": "FLOAT",
            "best_time_to_visit": "VARCHAR(160) NOT NULL DEFAULT ''",
            "verification_status": "VARCHAR(40) NOT NULL DEFAULT 'unverified'",
            "cost_basis": "VARCHAR(20) NOT NULL DEFAULT 'unverified'",
            "is_demo": "BOOLEAN NOT NULL DEFAULT FALSE",
            "source_url": "TEXT NOT NULL DEFAULT ''",
        },
        "transport_service": {
            "destination_id": "INTEGER REFERENCES destination (id)",
            "price_basis": "VARCHAR(20) NOT NULL DEFAULT 'unverified'",
            "is_demo": "BOOLEAN NOT NULL DEFAULT FALSE",
            "availability_verified": "BOOLEAN NOT NULL DEFAULT FALSE",
            "source_url": "TEXT NOT NULL DEFAULT ''",
            "duration": "VARCHAR(80) NOT NULL DEFAULT ''",
            "distance_km": "VARCHAR(80) NOT NULL DEFAULT ''",
            "origin_station": "VARCHAR(160) NOT NULL DEFAULT ''",
            "destination_station": "VARCHAR(160) NOT NULL DEFAULT ''",
            "available_classes": "VARCHAR(160) NOT NULL DEFAULT ''",
            "class_fares": "TEXT NOT NULL DEFAULT ''",
            "pricing_unit": "VARCHAR(40) NOT NULL DEFAULT 'per_person'",
            "contact_number": "VARCHAR(80) NOT NULL DEFAULT ''",
            "booking_url": "TEXT NOT NULL DEFAULT ''",
            "boarding_point": "VARCHAR(160) NOT NULL DEFAULT ''",
            "dropping_point": "VARCHAR(160) NOT NULL DEFAULT ''",
            "booking_status": "VARCHAR(80) NOT NULL DEFAULT 'Available'",
            "is_daily": "BOOLEAN NOT NULL DEFAULT TRUE",
        },
    }
    inspector = inspect(db.engine)
    with db.engine.begin() as connection:
        for table_name, columns in additions.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(
                        f'ALTER TABLE "{table_name}" ADD COLUMN "{name}" {definition}'
                    ))
        connection.execute(text("""
            UPDATE room_type
            SET total_rooms = available_rooms + COALESCE((
                SELECT SUM(booking.rooms_count)
                FROM booking
                WHERE booking.room_type_id = room_type.id
                    AND booking.status != 'cancelled'
            ), 0)
            WHERE total_rooms IS NULL AND available_rooms IS NOT NULL
        """))
        # Ensure taxi records are deactivated and excluded
        connection.execute(text("""
            UPDATE transport_service
            SET active = 0
            WHERE LOWER(mode) IN ('taxi', 'transfer', 'cab')
        """))

    # Seed comprehensive demo bus & train options across all destinations (bypassed in unit tests)
    if os.environ.get("DATABASE_URL") != "sqlite://" and not app.config.get("TESTING"):
        try:
            from transport_generator import seed_all_destination_demo_transport
            seed_all_destination_demo_transport(db, Destination, TransportService)
        except Exception:
            pass


def destination_json(row: Destination, include_attractions: bool = False) -> dict:
    dest_data = {
        "id": row.id,
        "name": row.name,
        "state": row.state or row.region,
        "region": row.region,
        "description": row.description,
        "image_url": row.image_url,
        "best_time_to_visit": row.best_time_to_visit or "October to March",
        "budget_range": row.budget_range or "₹2,500 – ₹5,500 / day",
        "active": row.active,
        "attractions_count": len([a for a in row.attractions if a.active]) if hasattr(row, "attractions") and row.attractions else 0,
    }
    if include_attractions and hasattr(row, "attractions") and row.attractions:
        dest_data["attractions"] = [attraction_json(a) for a in row.attractions if a.active]
    return dest_data


def generate_hotel_map_url(row: Hotel) -> str:
    if not row:
        return ""
    if getattr(row, "google_maps_url", ""):
        return row.google_maps_url
    if getattr(row, "latitude", None) is not None and getattr(row, "longitude", None) is not None:
        return f"https://www.google.com/maps/search/?api=1&query={row.latitude},{row.longitude}"
    from urllib.parse import quote_plus
    parts = [row.name]
    if getattr(row, "address", ""):
        parts.append(row.address)
    elif getattr(row, "destination", None):
        parts.append(row.destination.name)
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(', '.join(parts))}"


def hotel_json(row: Hotel) -> dict:
    return {
        "id": row.id,
        "destination_id": row.destination_id,
        "destination": row.destination.name if row.destination else "",
        "name": row.name,
        "description": getattr(row, "description", "") or "",
        "nightly_rate": float(row.nightly_rate),
        "active": row.active,
        "price_tier": row.price_tier,
        "price_basis": row.price_basis,
        "is_demo": row.is_demo,
        "source_url": row.source_url,
        "address": row.address or "",
        "google_maps_url": getattr(row, "google_maps_url", "") or generate_hotel_map_url(row),
        "latitude": float(row.latitude) if getattr(row, "latitude", None) is not None else None,
        "longitude": float(row.longitude) if getattr(row, "longitude", None) is not None else None,
        "image_url": row.image_url or "",
        "check_in_policy": getattr(row, "check_in_policy", "") or "14:00",
        "check_out_policy": getattr(row, "check_out_policy", "") or "11:00",
        "rating": row.profile.rating if row.profile else None,
        "rating_verified": row.profile.rating_verified if row.profile else False,
        "facilities": row.profile.facilities if row.profile else [],
        "rooms": [
            room_type_json(room)
            for room in sorted(row.rooms, key=lambda item: item.nightly_rate)
            if room.active
        ],
    }


def room_type_json(row: RoomType) -> dict:
    inventory = row.total_rooms if row.total_rooms is not None else row.available_rooms
    return {"id": row.id, "hotel_id": row.hotel_id, "name": row.name,
            "nightly_rate": float(row.nightly_rate), "capacity": row.capacity,
            "available_rooms": inventory, "total_rooms": inventory,
            "price_basis": row.price_basis, "active": row.active}


def attraction_json(row: TouristAttraction) -> dict:
    dest_name = row.destination.name if row.destination else ""
    entry = float(row.entry_fee) if row.entry_fee is not None else float(row.estimated_cost)
    return {
        "id": row.id,
        "destination_id": row.destination_id,
        "destination": dest_name,
        "name": row.name,
        "description": row.description,
        "category": row.category,
        "interests": row.interests or [],
        "image_url": row.image_url or "",
        "duration_hours": row.duration_hours,
        "opening_hours": row.opening_hours or "",
        "entry_fee": entry,
        "estimated_cost": float(row.estimated_cost),
        "latitude": row.latitude,
        "longitude": row.longitude,
        "best_time_to_visit": row.best_time_to_visit or "",
        "verification_status": row.verification_status or "verified",
        "active": row.active,
        "cost_basis": row.cost_basis,
        "is_demo": row.is_demo,
        "source_url": row.source_url or "",
    }


def transport_service_json(row: TransportService) -> dict:
    source_link = getattr(row, "booking_url", "") or getattr(row, "source_url", "") or ""
    fares = getattr(row, "class_fares", {})
    if isinstance(fares, str):
        try:
            import json as _json
            fares = _json.loads(fares) if fares else {}
        except Exception:
            fares = {}

    return {
        "id": row.id,
        "mode": row.mode,
        "category": row.mode,
        "origin": row.origin,
        "destination": row.destination,
        "destination_id": row.destination_id,
        "operator": row.operator,
        "service_name": getattr(row, "service_name", "") or "",
        "service_type": getattr(row, "service_type", "") or "",
        "departure_time": getattr(row, "departure_time", "") or "",
        "arrival_time": getattr(row, "arrival_time", "") or "",
        "duration": getattr(row, "duration", "") or "",
        "distance_km": getattr(row, "distance_km", "") or "",
        "origin_station": getattr(row, "origin_station", "") or "",
        "destination_station": getattr(row, "destination_station", "") or "",
        "available_classes": getattr(row, "available_classes", "") or "",
        "class_fares": fares if isinstance(fares, dict) else {},
        "pricing_unit": getattr(row, "pricing_unit", "per_person") or "per_person",
        "contact_number": getattr(row, "contact_number", "") or "",
        "booking_url": source_link,
        "source_url": source_link,
        "service_date": row.service_date.isoformat() if row.service_date else None,
        "is_daily": getattr(row, "is_daily", True),
        "ticket_price": float(row.ticket_price) if row.ticket_price is not None else 0.0,
        "available_seats": row.available_seats,
        "boarding_point": getattr(row, "boarding_point", "") or "",
        "dropping_point": getattr(row, "dropping_point", "") or "",
        "booking_status": getattr(row, "booking_status", "Available") or "Available",
        "availability_verified": bool(row.availability_verified),
        "availability_updated_at": row.availability_updated_at.isoformat() if row.availability_updated_at else None,
        "availability_source": "Verified operator schedule / estimated catalog data",
        "price_basis": row.price_basis or "estimate",
        "is_demo": bool(row.is_demo),
        "active": bool(row.active),
    }


def transport_reservation_json(row: TransportReservation) -> dict:
    return {
        "id": row.id, "service_id": row.service_id, "mode": row.service.mode,
        "origin": row.service.origin, "destination": row.service.destination,
        "operator": row.service.operator, "service_date": row.service.service_date.isoformat(),
        "departure_time": row.service.departure_time, "arrival_time": row.service.arrival_time,
        "seats": row.seats, "amount": float(row.amount), "status": row.status,
        "created_at": row.created_at.isoformat(),
    }


def booking_json(row: Booking, include_customer: bool = False) -> dict:
    ref = getattr(row, "booking_reference", "") or f"BK-{row.id:06d}"
    result = {
        "id": row.id,
        "booking_reference": ref,
        "reference": ref,
        "destination": row.destination.name if row.destination else "",
        "destination_id": row.destination_id,
        "hotel": row.hotel.name if row.hotel else "",
        "hotel_id": row.hotel_id,
        "hotel_address": row.hotel.address if row.hotel else "",
        "hotel_google_maps_url": generate_hotel_map_url(row.hotel) if row.hotel else "",
        "hotel_latitude": float(row.hotel.latitude) if (row.hotel and getattr(row.hotel, "latitude", None) is not None) else None,
        "hotel_longitude": float(row.hotel.longitude) if (row.hotel and getattr(row.hotel, "longitude", None) is not None) else None,
        "check_in": row.check_in.isoformat(),
        "room_type": row.room_type.name if row.room_type else None,
        "room_type_id": row.room_type_id,
        "check_out": row.check_out.isoformat(),
        "guests": row.guests,
        "rooms": row.rooms_count,
        "amount": float(row.amount),
        "is_demo": row.is_demo,
        "payment_status": row.payments[0].status if row.payments else "unpaid",
        "status": row.status,
        "created_at": row.created_at.isoformat(),
    }
    if include_customer and row.customer:
        result.update(customer_name=row.customer.name, customer_email=row.customer.email)
    return result


def saved_itinerary_json(row: SavedItinerary) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "destination_id": row.destination_id,
        "destination_name": row.destination.name if row.destination else "",
        "destination_image": row.destination.image_url if row.destination else "",
        "destination_state": (row.destination.state or row.destination.region) if row.destination else "",
        "title": row.title,
        "days": row.days,
        "travelers": row.travelers,
        "budget_per_person": float(row.budget_per_person),
        "total_budget": float(row.total_budget),
        "estimated_accommodation": float(row.estimated_accommodation),
        "estimated_transport": float(row.estimated_transport),
        "estimated_food": float(row.estimated_food),
        "estimated_sightseeing": float(row.estimated_sightseeing),
        "total_estimated_cost": float(row.total_estimated_cost),
        "cost_per_person": float(row.cost_per_person),
        "remaining_budget": float(row.remaining_budget),
        "within_budget": row.within_budget,
        "itinerary_data": row.itinerary_data,
        "generation_mode": row.generation_mode,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def filtered_bookings():
    query = Booking.query.join(User, Booking.user_id == User.id).join(Destination).join(Hotel).options(
        joinedload(Booking.customer), joinedload(Booking.destination), joinedload(Booking.hotel),
        joinedload(Booking.room_type),
        selectinload(Booking.payments),
    )
    search = request.args.get("search", "").strip()
    if search:
        pattern = f"%{search}%"
        filters = [
            User.name.ilike(pattern),
            User.email.ilike(pattern),
            Destination.name.ilike(pattern),
            Hotel.name.ilike(pattern),
            cast(Booking.id, String).ilike(pattern),
            Booking.booking_reference.ilike(pattern),
        ]
        clean_num = search.upper().replace("BK-", "").lstrip("0")
        if clean_num.isdigit():
            filters.append(Booking.id == int(clean_num))
        query = query.filter(or_(*filters))
    if request.args.get("status"):
        query = query.filter(Booking.status == request.args["status"])
    if request.args.get("destination_id", type=int):
        query = query.filter(Booking.destination_id == request.args.get("destination_id", type=int))
    if request.args.get("payment_status"):
        query = query.filter(Booking.payments.any(Payment.status == request.args["payment_status"]))
    for key in ("from_date", "to_date"):
        value = request.args.get(key)
        if value:
            try:
                bound = datetime.combine(date.fromisoformat(value), datetime.min.time(), tzinfo=timezone.utc)
            except ValueError:
                raise BadRequest(f"Invalid {key}; use YYYY-MM-DD.")
            if key == "to_date":
                bound += timedelta(days=1)
                query = query.filter(Booking.created_at < bound)
            else:
                query = query.filter(Booking.created_at >= bound)
    return query.order_by(Booking.created_at.desc()).all()


app = create_app()
with app.app_context():
    upgrade_database_schema()

