"""
ROAMLY Transport Data Generator
Generates realistic, deterministic demo bus (5 options) and demo train (5 options)
for every supported city-to-city route across all destinations in India.

Features:
- Deterministic schedules across 5 time slots (Early Morning, Late Morning, Afternoon, Evening, Night)
- Different timings and durations for forward vs reverse routes
- Hill stations (Ooty, Manali) transparently routed through nearest verified railheads
  (Mettupalayam/Coimbatore for Ooty; Chandigarh/Kalka for Manali)
- Clear [DEMO] labeling for academic integrity
- Avoids duplicate records on server restart
"""

import math
from datetime import date, timedelta
from decimal import Decimal

# Supported destination/city metadata with verified station hubs & coordinates
CITY_PROFILES = {
    "Hyderabad": {
        "name": "Hyderabad",
        "state": "Telangana",
        "lat": 17.3850,
        "lon": 78.4867,
        "bus_terminals": [
            "MGBS Central Bus Station (Imlibun), Hyderabad",
            "Jubilee Bus Station (JBS), Secunderabad",
            "Gachibowli ORR Terminal, Hyderabad",
            "Ameerpet Metro Transit Hub, Hyderabad",
            "Dilsukhnagar Bus Complex, Hyderabad",
        ],
        "train_stations": [
            "Secunderabad Junction (SC)",
            "Hyderabad Deccan Nampally (HYB)",
            "Kacheguda Railway Station (KCG)",
            "Secunderabad Junction (SC)",
            "Hyderabad Deccan (HYB)",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Bengaluru": {
        "name": "Bengaluru",
        "state": "Karnataka",
        "lat": 12.9716,
        "lon": 77.5946,
        "bus_terminals": [
            "Kempegowda Bus Station (Majestic), Bengaluru",
            "Shantinagar Bus Station, Bengaluru",
            "Madiwala Intercity Bus Point, Bengaluru",
            "Yesvantpur BMTC / KSRTC Hub, Bengaluru",
            "Electronic City Toll Gate Terminal, Bengaluru",
        ],
        "train_stations": [
            "KSR Bengaluru City Junction (SBC)",
            "Yesvantpur Junction (YPR)",
            "SMVT Bengaluru (SMVB)",
            "KSR Bengaluru City (SBC)",
            "Cantonment Railway Station (BNC)",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Chennai": {
        "name": "Chennai",
        "state": "Tamil Nadu",
        "lat": 13.0827,
        "lon": 80.2707,
        "bus_terminals": [
            "CMBT Koyambedu Bus Terminus, Chennai",
            "Kilambakkam Bus Terminus (KCBT), Chennai",
            "Guindy Kathipara Junction, Chennai",
            "Tambaram Sanatorium Bus Stand, Chennai",
            "Madhavaram Intercity Terminal, Chennai",
        ],
        "train_stations": [
            "Puratchi Thalaivar Dr. MGR Chennai Central (MAS)",
            "Chennai Egmore Railway Station (MS)",
            "Tambaram Railway Station (TBM)",
            "Puratchi Thalaivar Dr. MGR Central (MAS)",
            "Chennai Egmore (MS)",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Goa": {
        "name": "Goa",
        "state": "Goa",
        "lat": 15.2993,
        "lon": 74.1240,
        "bus_terminals": [
            "Panaji KTC Central Bus Stand, Goa",
            "Mapusa KTC Bus Stand, North Goa",
            "Margao KTC Bus Terminus, South Goa",
            "Calangute Beach Transit Point, North Goa",
            "Vasco KTC Bus Stand, Goa",
        ],
        "train_stations": [
            "Madgaon Junction (MAO), Goa",
            "Vasco-da-Gama Railway Station (VSG), Goa",
            "Thivim Railway Station (THVM), North Goa",
            "Karmali Railway Station (KRMI), Goa",
            "Madgaon Junction (MAO), Goa",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Mumbai": {
        "name": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0760,
        "lon": 72.8777,
        "bus_terminals": [
            "Borivali West Nancy Colony Bus Stand, Mumbai",
            "Dadar TT Circle Terminal, Mumbai",
            "Vashi Highway Plaza, Navi Mumbai",
            "Sion Circle Transit Depot, Mumbai",
            "Thane Teen Hath Naka Bus Hub, Mumbai",
        ],
        "train_stations": [
            "Chhatrapati Shivaji Maharaj Terminus (CSMT), Mumbai",
            "Mumbai Central Railway Station (MMCT)",
            "Bandra Terminus (BDTS), Mumbai",
            "Lokmanya Tilak Terminus (LTT), Kurla",
            "Dadar Junction (DR), Mumbai",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Delhi": {
        "name": "Delhi",
        "state": "Delhi",
        "lat": 28.6139,
        "lon": 77.2090,
        "bus_terminals": [
            "Kashmere Gate ISBT (Maharana Pratap), Delhi",
            "Anand Vihar ISBT (Swami Vivekanand), Delhi",
            "Sarai Kale Khan ISBT, Delhi",
            "Dhaula Kuan Transit Hub, New Delhi",
            "Majnu Ka Tila Tourist Bus Stand, Delhi",
        ],
        "train_stations": [
            "New Delhi Railway Station (NDLS)",
            "Hazrat Nizamuddin Railway Station (NZM)",
            "Anand Vihar Terminal (ANVT)",
            "Delhi Sarai Rohilla (DEE)",
            "Old Delhi Railway Station (DLI)",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Agra": {
        "name": "Agra",
        "state": "Uttar Pradesh",
        "lat": 27.1767,
        "lon": 78.0081,
        "bus_terminals": [
            "ISBT Transport Nagar, Agra",
            "Idgah Central Bus Stand, Agra",
            "Water Works Crossing Bus Hub, Agra",
            "Taj East Gate Tourist Transit Point, Agra",
            "Raja Ki Mandi Bus Stop, Agra",
        ],
        "train_stations": [
            "Agra Cantt Railway Station (AGC)",
            "Agra Fort Railway Station (AF)",
            "Raja Ki Mandi Station (RKM)",
            "Agra Cantt (AGC)",
            "Tundla Junction (TDL) [Agra Hub]",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Jaipur": {
        "name": "Jaipur",
        "state": "Rajasthan",
        "lat": 26.9124,
        "lon": 75.7873,
        "bus_terminals": [
            "Sindhi Camp Central ISBT, Jaipur",
            "Narayan Singh Circle Bus Stand, Jaipur",
            "200 Feet Ajmer Bypass Hub, Jaipur",
            "Transport Nagar Bus Stand, Jaipur",
            "Durgapura Transit Point, Jaipur",
        ],
        "train_stations": [
            "Jaipur Junction (JP)",
            "Gandhinagar Jaipur (GADJ)",
            "Durgapura Railway Station (DPA)",
            "Jaipur Junction (JP)",
            "Kanakpura Station (KKU)",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Varanasi": {
        "name": "Varanasi",
        "state": "Uttar Pradesh",
        "lat": 25.3176,
        "lon": 82.9739,
        "bus_terminals": [
            "Varanasi Cantt UPSRTC Roadways Bus Stand",
            "Englishia Line Intercity Depot, Varanasi",
            "Lanka BHU Bus Stop, Varanasi",
            "Pandeypur Crossroads Terminal, Varanasi",
            "Babatpur Highway Transit Junction, Varanasi",
        ],
        "train_stations": [
            "Varanasi Junction Cantt (BSB)",
            "Banaras Railway Station (BSBS)",
            "Pt. Deen Dayal Upadhyaya Junction (DDU) [Mughalsarai]",
            "Varanasi City Station (BCY)",
            "Kashi Railway Station (KEI)",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Rishikesh": {
        "name": "Rishikesh",
        "state": "Uttarakhand",
        "lat": 30.0869,
        "lon": 78.2676,
        "bus_terminals": [
            "Rishikesh Central ISBT (Haridwar Road)",
            "Natraj Chowk Transit Stand, Rishikesh",
            "Muni Ki Reti Tourist Bus Depot, Rishikesh",
            "Tapovan Transit Crossing, Rishikesh",
            "Nepali Farm Highway Terminal, Rishikesh",
        ],
        "train_stations": [
            "Yog Nagari Rishikesh (YNRK)",
            "Haridwar Junction (HW) [Major Railhead 25km from Rishikesh]",
            "Yog Nagari Rishikesh (YNRK)",
            "Rishikesh Railway Station (RKSH)",
            "Haridwar Junction (HW) [Connecting Junction for Rishikesh]",
        ],
        "has_direct_train": True,
        "rail_note": "Direct broad-gauge rail serves Yog Nagari Rishikesh; Haridwar Junction (25 km away) serves extensive pan-India express trains.",
    },
    "Mysuru": {
        "name": "Mysuru",
        "state": "Karnataka",
        "lat": 12.2958,
        "lon": 76.6394,
        "bus_terminals": [
            "Mysuru Suburb KSRTC Bus Stand",
            "Mysuru City Central Stand (Near Palace)",
            "Columbia Asia Signal Depot, Mysuru",
            "Hunsur Road Junction, Mysuru",
            "Ring Road Transit Terminal, Mysuru",
        ],
        "train_stations": [
            "Mysuru Junction (MYS)",
            "Mysuru Junction (MYS)",
            "Ashokapuram Railway Station (AP)",
            "Mysuru Junction (MYS)",
            "Naganahalli Station (NHY)",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Ooty": {
        "name": "Ooty",
        "state": "Tamil Nadu",
        "lat": 11.4102,
        "lon": 76.6950,
        "bus_terminals": [
            "Ooty Central Government Bus Stand (ATC)",
            "Charring Cross Tourist Terminal, Ooty",
            "Botanical Garden Bus Stop, Ooty",
            "Fingerpost Junction, Ooty",
            "Lovedale Road Transit Point, Ooty",
        ],
        "train_stations": [
            "Mettupalayam (MTP) [Nearest Broad-Gauge Railhead for Ooty - Connect via Toy Train / Ghat Road]",
            "Coimbatore Junction (CBE) [Major Rail Junction for Ooty - 85km via Nilgiri Ghat Road]",
            "Mettupalayam Railway Station (MTP) [Connecting Station for Ooty]",
            "Coimbatore Junction (CBE) [Connecting Hub for Ooty]",
            "Mettupalayam (MTP) [Nilgiri Mountain Rail Junction for Ooty]",
        ],
        "has_direct_train": False,
        "rail_note": "No direct broad-gauge railway to Ooty hill station. Express trains terminate at Mettupalayam (MTP) or Coimbatore (CBE); transfer to the Nilgiri Toy Train or road taxi/bus.",
    },
    "Manali": {
        "name": "Manali",
        "state": "Himachal Pradesh",
        "lat": 32.2396,
        "lon": 77.1887,
        "bus_terminals": [
            "Manali Private Bus Stand (Near Mall Road)",
            "HRTC Central Bus Stand, Manali",
            "Patlikuhl Crossing Highway Terminal, Manali",
            "Aleo Transit Point, Manali",
            "Kullu-Manali Highway Bypass Stand",
        ],
        "train_stations": [
            "Chandigarh Junction (CDG) [Nearest Major Railhead for Manali - Connect via Highway transfer]",
            "Kalka Railway Station (KLK) [Connecting Railhead for Manali via Himalayan Highway]",
            "Chandigarh Junction (CDG) [Major Rail Transit Hub for Manali]",
            "Kalka Railway Station (KLK) [Connecting Station for Manali]",
            "Ambala Cantt Junction (UMB) [Express Rail Junction connecting Manali]",
        ],
        "has_direct_train": False,
        "rail_note": "No direct railway line to Manali hill station. Rail travel terminates at Chandigarh (CDG) or Kalka (KLK); transfer by road via the scenic Kullu-Manali expressway.",
    },
    "Kerala": {
        "name": "Kerala",
        "state": "Kerala",
        "lat": 9.9312,
        "lon": 76.2673,
        "bus_terminals": [
            "Vytilla Mobility Hub, Kochi, Kerala",
            "KSRTC Central Bus Station, Ernakulam, Kerala",
            "Edappally Toll Transit Hub, Kochi, Kerala",
            "Aluva KSRTC Bus Stand, Kerala",
            "Kaloor Private Bus Terminal, Kochi, Kerala",
        ],
        "train_stations": [
            "Ernakulam Junction South (ERS), Kerala",
            "Ernakulam Town North (ERN), Kerala",
            "Aluva Railway Station (AWY), Kerala",
            "Ernakulam Junction (ERS), Kerala",
            "Thrissur Railway Station (TCR) [Kerala Hub]",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
    "Tamil Nadu": {
        "name": "Tamil Nadu",
        "state": "Tamil Nadu",
        "lat": 13.0827,
        "lon": 80.2707,
        "bus_terminals": [
            "CMBT Koyambedu Central Bus Terminal, Tamil Nadu",
            "Kilambakkam Intercity Bus Terminus (KCBT), Tamil Nadu",
            "Guindy Kathipara Hub, Tamil Nadu",
            "Madurai Mattuthavani Bus Stand, Tamil Nadu",
            "Coimbatore Gandhipuram Central Stand, Tamil Nadu",
        ],
        "train_stations": [
            "Puratchi Thalaivar Dr. MGR Chennai Central (MAS)",
            "Chennai Egmore Railway Station (MS)",
            "Coimbatore Junction (CBE), Tamil Nadu",
            "Madurai Junction (MDU), Tamil Nadu",
            "Tiruchchirappalli Junction (TPJ), Tamil Nadu",
        ],
        "has_direct_train": True,
        "rail_note": "",
    },
}

# 5 Defined Bus Slots (Early morning, Late morning, Afternoon, Evening, Night)
BUS_SLOT_CONFIGS = [
    {
        "slot_id": 1,
        "slot_name": "Early Morning",
        "fwd_dep": "06:15",
        "rev_dep": "05:45",
        "operator": "IntrCity SmartBus (Demo)",
        "service_type": "BharatBenz AC Sleeper (2+1)",
        "fare_factor": 1.55,
        "min_fare": 380,
        "seats": 28,
        "speed_factor": 1.0,
    },
    {
        "slot_id": 2,
        "slot_name": "Late Morning",
        "fwd_dep": "10:30",
        "rev_dep": "11:15",
        "operator": "Orange Tours & Travels (Demo)",
        "service_type": "Volvo Multi-Axle 9600 AC Semi-Sleeper",
        "fare_factor": 1.85,
        "min_fare": 480,
        "seats": 34,
        "speed_factor": 0.95,
    },
    {
        "slot_id": 3,
        "slot_name": "Afternoon",
        "fwd_dep": "14:45",
        "rev_dep": "13:30",
        "operator": "SRS Travels & Logistics (Demo)",
        "service_type": "Scania High-Deck AC Seater (2+2)",
        "fare_factor": 1.65,
        "min_fare": 420,
        "seats": 22,
        "speed_factor": 0.92,
    },
    {
        "slot_id": 4,
        "slot_name": "Evening",
        "fwd_dep": "18:30",
        "rev_dep": "19:15",
        "operator": "Zingbus Electric & Multi-Axle (Demo)",
        "service_type": "Premium Electric AC Luxury Sleeper",
        "fare_factor": 2.20,
        "min_fare": 580,
        "seats": 18,
        "speed_factor": 1.02,
    },
    {
        "slot_id": 5,
        "slot_name": "Night",
        "fwd_dep": "22:15",
        "rev_dep": "21:45",
        "operator": "VRL Travel Lines (Demo)",
        "service_type": "Ultra-Deluxe All-Weather AC Sleeper (2+1)",
        "fare_factor": 2.45,
        "min_fare": 650,
        "seats": 31,
        "speed_factor": 1.08,
    },
]

# 5 Defined Train Slots (Morning, Late Morning, Afternoon, Evening, Night)
TRAIN_SLOT_CONFIGS = [
    {
        "slot_id": 1,
        "slot_name": "Morning",
        "fwd_dep": "06:00",
        "rev_dep": "06:45",
        "title_template": "[DEMO] {origin} - {dest} Vande Bharat Express",
        "ooty_title": "[DEMO] Vande Bharat Link (via MTP for Ooty)",
        "manali_title": "[DEMO] Himalayan Vande Bharat (via Chandigarh for Manali)",
        "classes": "Chair Car (CC), Executive Class (EC)",
        "fare_factor": 1.60,
        "min_fare": 550,
        "seats": 68,
        "speed_factor": 1.25,
    },
    {
        "slot_id": 2,
        "slot_name": "Late Morning",
        "fwd_dep": "09:30",
        "rev_dep": "10:15",
        "title_template": "[DEMO] {origin} - {dest} Superfast Intercity Express",
        "ooty_title": "[DEMO] Nilgiri Superfast Express (via Mettupalayam)",
        "manali_title": "[DEMO] Shivalik Express Link (via Kalka for Manali)",
        "classes": "Second Sitting (2S), AC Chair Car (CC), 3AC",
        "fare_factor": 0.95,
        "min_fare": 320,
        "seats": 112,
        "speed_factor": 1.0,
    },
    {
        "slot_id": 3,
        "slot_name": "Afternoon",
        "fwd_dep": "13:50",
        "rev_dep": "14:20",
        "title_template": "[DEMO] {origin} - {dest} Jan Shatabdi Express",
        "ooty_title": "[DEMO] Coimbatore Intercity Express (Connecting Ooty)",
        "manali_title": "[DEMO] Northern Valley Superfast (via Chandigarh for Manali)",
        "classes": "Sleeper (SL), 3AC Economy (3E), 3AC",
        "fare_factor": 1.10,
        "min_fare": 380,
        "seats": 84,
        "speed_factor": 1.05,
    },
    {
        "slot_id": 4,
        "slot_name": "Evening",
        "fwd_dep": "17:40",
        "rev_dep": "18:15",
        "title_template": "[DEMO] {origin} - {dest} Rajdhani Deluxe Superfast",
        "ooty_title": "[DEMO] Western Ghats Deluxe Express (via MTP)",
        "manali_title": "[DEMO] Himachal Rajdhani Link (via Chandigarh for Manali)",
        "classes": "3AC, 2AC, First AC (1A)",
        "fare_factor": 2.10,
        "min_fare": 750,
        "seats": 46,
        "speed_factor": 1.18,
    },
    {
        "slot_id": 5,
        "slot_name": "Night",
        "fwd_dep": "21:15",
        "rev_dep": "22:30",
        "title_template": "[DEMO] {origin} - {dest} Overnight Express Liner",
        "ooty_title": "[DEMO] Blue Mountain Night Express (via Coimbatore)",
        "manali_title": "[DEMO] Pine Valley Overnight Express (via Kalka for Manali)",
        "classes": "Sleeper (SL), 3AC, 2AC",
        "fare_factor": 1.25,
        "min_fare": 450,
        "seats": 98,
        "speed_factor": 1.05,
    },
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371.0 * c


def get_corridor_distance(origin_name: str, dest_name: str) -> int:
    prof_a = CITY_PROFILES.get(origin_name)
    prof_b = CITY_PROFILES.get(dest_name)
    if not prof_a or not prof_b:
        return 500

    crow = haversine_km(prof_a["lat"], prof_a["lon"], prof_b["lat"], prof_b["lon"])
    # Mountainous or hilly terrain has higher winding ratio
    is_hill = origin_name in ("Ooty", "Manali", "Rishikesh") or dest_name in ("Ooty", "Manali", "Rishikesh")
    factor = 1.36 if is_hill else 1.26
    dist = max(110, int(round(crow * factor / 5.0) * 5))
    return dist


def calculate_arrival(dep_hhmm: str, duration_mins: int) -> tuple[str, str]:
    dh, dm = map(int, dep_hhmm.split(":"))
    dep_total = dh * 60 + dm
    arr_total = dep_total + duration_mins
    arr_days = arr_total // 1440
    rem = arr_total % 1440
    ah = rem // 60
    am = rem % 60

    dur_h = duration_mins // 60
    dur_m = duration_mins % 60
    dur_str = f"{dur_h}h {dur_m:02d}m" if dur_m > 0 else f"{dur_h}h 00m"

    if arr_days == 1:
        arr_str = f"{ah:02d}:{am:02d} (+1 day)"
    elif arr_days > 1:
        arr_str = f"{ah:02d}:{am:02d} (+{arr_days} days)"
    else:
        arr_str = f"{ah:02d}:{am:02d}"

    return arr_str, dur_str


def is_reverse_route(origin: str, dest: str) -> bool:
    """Consistently identifies whether (origin, dest) is the canonical forward or reverse direction."""
    return origin.lower() > dest.lower()


def generate_demo_buses_for_route(origin: str, dest: str, destination_id: int | None = None) -> list[dict]:
    prof_orig = CITY_PROFILES.get(origin) or CITY_PROFILES["Hyderabad"]
    prof_dest = CITY_PROFILES.get(dest) or CITY_PROFILES["Goa"]
    road_km = get_corridor_distance(origin, dest)
    is_rev = is_reverse_route(origin, dest)

    is_mountain = origin in ("Ooty", "Manali") or dest in ("Ooty", "Manali")
    base_bus_speed = 38.0 if is_mountain else 55.0

    buses = []
    orig_code = origin[:3].upper()
    dest_code = dest[:3].upper()

    for idx, cfg in enumerate(BUS_SLOT_CONFIGS):
        slot_num = idx + 1
        dep_time = cfg["rev_dep"] if is_rev else cfg["fwd_dep"]
        effective_speed = base_bus_speed * cfg["speed_factor"]
        duration_mins = max(120, int(round((road_km / effective_speed) * 60)))
        arr_time, dur_str = calculate_arrival(dep_time, duration_mins)

        fare = max(cfg["min_fare"], int(round((road_km * cfg["fare_factor"]) / 10.0) * 10))
        board_point = prof_orig["bus_terminals"][idx % len(prof_orig["bus_terminals"])]
        drop_point = prof_dest["bus_terminals"][idx % len(prof_dest["bus_terminals"])]

        service_id_code = f"DEMO-BUS-{orig_code}{dest_code}-0{slot_num}"
        service_name = f"[DEMO] {origin} to {dest} {cfg['slot_name']} Express ({service_id_code})"

        buses.append({
            "destination_id": destination_id,
            "mode": "bus",
            "operator": cfg["operator"],
            "service_name": service_name,
            "service_type": cfg["service_type"],
            "origin": origin,
            "origin_station": board_point,
            "destination": dest,
            "destination_station": drop_point,
            "boarding_point": board_point,
            "dropping_point": drop_point,
            "booking_status": f"Available - {cfg['seats']} demo seats",
            "departure_time": dep_time,
            "arrival_time": arr_time,
            "duration": dur_str,
            "distance_km": f"{road_km} km",
            "ticket_price": Decimal(str(fare)),
            "available_seats": cfg["seats"],
            "available_classes": "AC Sleeper / Seater",
            "class_fares": {"Standard": fare},
            "pricing_unit": "per_person",
            "contact_number": "1800-DEMO-BUS",
            "booking_url": "https://www.redbus.in",
            "source_url": "https://www.redbus.in",
            "is_daily": True,
            "service_date": date.today(),
            "availability_verified": False,
            "price_basis": "estimate",
            "is_demo": True,
            "active": True,
        })

    return buses


def generate_demo_trains_for_route(origin: str, dest: str, destination_id: int | None = None) -> list[dict]:
    prof_orig = CITY_PROFILES.get(origin) or CITY_PROFILES["Hyderabad"]
    prof_dest = CITY_PROFILES.get(dest) or CITY_PROFILES["Chennai"]
    road_km = get_corridor_distance(origin, dest)
    is_rev = is_reverse_route(origin, dest)

    trains = []
    orig_code = origin[:3].upper()
    dest_code = dest[:3].upper()

    for idx, cfg in enumerate(TRAIN_SLOT_CONFIGS):
        slot_num = idx + 1
        dep_time = cfg["rev_dep"] if is_rev else cfg["fwd_dep"]

        # Train speed averaging 70-95 km/h
        base_speed = 72.0
        effective_speed = base_speed * cfg["speed_factor"]
        duration_mins = max(90, int(round((road_km / effective_speed) * 60)))
        arr_time, dur_str = calculate_arrival(dep_time, duration_mins)

        fare = max(cfg["min_fare"], int(round((road_km * cfg["fare_factor"]) / 10.0) * 10))
        orig_station = prof_orig["train_stations"][idx % len(prof_orig["train_stations"])]
        dest_station = prof_dest["train_stations"][idx % len(prof_dest["train_stations"])]

        train_code = f"DEMO-TRN-{orig_code}{dest_code}-0{slot_num}"

        if dest == "Ooty":
            train_name = f"{cfg['ooty_title']} ({train_code})"
        elif dest == "Manali":
            train_name = f"{cfg['manali_title']} ({train_code})"
        elif origin == "Ooty":
            train_name = f"[DEMO] Nilgiri Express Return (Connecting from Ooty via MTP) ({train_code})"
        elif origin == "Manali":
            train_name = f"[DEMO] Himalayan Rail Return (Connecting from Manali via Chandigarh) ({train_code})"
        else:
            title_base = cfg["title_template"].format(origin=origin, dest=dest)
            train_name = f"{title_base} ({train_code})"

        trains.append({
            "destination_id": destination_id,
            "mode": "train",
            "operator": "Indian Railways / IRCTC (Demo)",
            "service_name": train_name,
            "service_type": "Express Superfast Rail",
            "origin": origin,
            "origin_station": orig_station,
            "destination": dest,
            "destination_station": dest_station,
            "boarding_point": orig_station,
            "dropping_point": dest_station,
            "booking_status": f"Available - {cfg['seats']} demo seats",
            "departure_time": dep_time,
            "arrival_time": arr_time,
            "duration": dur_str,
            "distance_km": f"{road_km} km",
            "ticket_price": Decimal(str(fare)),
            "available_seats": cfg["seats"],
            "available_classes": cfg["classes"],
            "class_fares": {
                "Standard": fare,
                "Premium": int(fare * 1.5),
            },
            "pricing_unit": "per_person",
            "contact_number": "139 (Railway Inquiry Demo)",
            "booking_url": "https://www.irctc.co.in",
            "source_url": "https://www.irctc.co.in",
            "is_daily": True,
            "service_date": date.today(),
            "availability_verified": False,
            "price_basis": "estimate",
            "is_demo": True,
            "active": True,
        })

    return trains


def seed_all_destination_demo_transport(db, destination_model, transport_service_model) -> dict:
    """
    Populates exactly 5 demo buses and 5 demo trains for every supported pair of
    destinations in both directions.
    Guarantees no duplicate records are created when restarted.
    """
    destinations = destination_model.query.filter_by(active=True).all()
    if not destinations:
        return {"buses_added": 0, "trains_added": 0, "total_pairs": 0}

    dest_by_name = {d.name.lower(): d for d in destinations}
    city_names = [d.name for d in destinations if d.name in CITY_PROFILES]

    # Ensure all CITY_PROFILES keys that correspond to active destinations are represented
    if len(city_names) < 5:
        city_names = list(CITY_PROFILES.keys())

    # Build existing lookup map: (mode, lower(origin), lower(dest), departure_time) -> existing_record
    existing_records = transport_service_model.query.filter_by(is_demo=True).all()
    existing_map = {}
    for r in existing_records:
        key = (r.mode.lower(), r.origin.strip().lower(), r.destination.strip().lower(), r.departure_time.strip())
        existing_map[key] = r

    to_add = []
    pairs_count = 0
    buses_count = 0
    trains_count = 0

    for orig in city_names:
        for dest in city_names:
            if orig == dest:
                continue

            pairs_count += 1
            dest_obj = dest_by_name.get(dest.lower())
            dest_id = dest_obj.id if dest_obj else None

            # 5 Demo Buses
            bus_data_list = generate_demo_buses_for_route(orig, dest, dest_id)
            for b in bus_data_list:
                key = (b["mode"].lower(), b["origin"].lower(), b["destination"].lower(), b["departure_time"])
                if key not in existing_map:
                    to_add.append(transport_service_model(**b))
                    buses_count += 1

            # 5 Demo Trains
            train_data_list = generate_demo_trains_for_route(orig, dest, dest_id)
            for t in train_data_list:
                key = (t["mode"].lower(), t["origin"].lower(), t["destination"].lower(), t["departure_time"])
                if key not in existing_map:
                    to_add.append(transport_service_model(**t))
                    trains_count += 1

    if to_add:
        # Commit in reasonable batches
        batch_size = 500
        for i in range(0, len(to_add), batch_size):
            db.session.add_all(to_add[i:i + batch_size])
            db.session.commit()

    return {
        "pairs_covered": pairs_count,
        "new_buses_added": buses_count,
        "new_trains_added": trains_count,
        "total_new_services": len(to_add),
    }

