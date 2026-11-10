import json

# Curated 91 completely distinct, property-tailored Unsplash photo IDs
HOTEL_UNIQUE_IDS = {
    # 1. Goa (7 hotels)
    "Goa Heritage Palms Resort & Spa (Demo)": "photo-1582719508461-905c673771fd",
    "Taj Aguada Cliffside Resort & Spa": "photo-1571896349842-33c89424de2d",
    "Baga Blue Sands Boutique Hotel": "photo-1571003123894-1f0594d2b5d9",
    "Palolem Palm Bay Eco Resort": "photo-1520250497591-112f2f40a3f4",
    "Panaji Old Latin Quarter Inn": "photo-1582719478250-c89cae4dc85b",
    "Anjuna Sunset Cliffside Villas": "photo-1584132967334-10e028bd69f7",
    "The Grand Azure Bay Resort": "photo-1540541338287-41700207dee6",

    # 2. Hyderabad (6 hotels)
    "Hyderabad Charminar Heritage Grand (Demo)": "photo-1566073771259-6a8506099945",
    "Taj Falaknuma Palace Residency": "photo-1590490360182-c33d57733427",
    "HITEC City Silicon Boutique Hotel": "photo-1618773928121-c32242e63f39",
    "Hussain Sagar Lakeview Grand": "photo-1578683010236-d716f9a3f461",
    "Golconda Heritage Gate Inn": "photo-1566665797739-1674de7a421a",
    "Jubilee Hills Royal Court Hotel": "photo-1596394516093-501ba68a0ba6",

    # 3. Chennai (6 hotels)
    "Chennai Marina Bay Breeze Hotel (Demo)": "photo-1542314831-068cd1dbfeeb",
    "ITC Grand Chola Heritage Residency": "photo-1551882547-ff40c63fe5fa",
    "ECR Beach Haven Resort": "photo-1571896349842-48c89491295b",
    "Mylapore Heritage Temple Stay": "photo-1591088398332-8a7791972843",
    "T. Nagar Central Plaza Hotel": "photo-1568084680786-a84f91d1153c",
    "Nungambakkam Garden Court Hotel": "photo-1578683010344-934d402488a0",

    # 4. Ooty (6 hotels)
    "Nilgiri Mist Valley Retreat (Demo)": "photo-1587061949409-02df41d5e562",
    "Savoy Heritage Nilgiri Hill Resort": "photo-1596436889106-be35e843f974",
    "Doddabetta Peak Mountain Lodge": "photo-1510798831971-661eb04b3739",
    "Ooty Lake Pineview Cottages": "photo-1445019980597-93fa8acb246c",
    "Nilgiri Botanical Tea Estate Stay": "photo-1507652313519-d4e9174996dd",
    "Coonoor Mountain Breeze Inn": "photo-1470770841072-f978cf4d019e",

    # 5. Manali (6 hotels)
    "Himalayan Pine Glades Resort (Demo)": "photo-1548777123-e216912df7d8",
    "Solang Valley Alpine Luxury Chalet": "photo-1512917774080-9991f1c4c750",
    "Old Manali Riverside Wooden Cottages": "photo-1449844908441-8829872d2607",
    "Rohtang Foothills Snowcrest Resort": "photo-1486406146926-c627a92ad1ab",
    "Mall Road Central Grand Stay": "photo-1564501049412-61c2a3083791",
    "Vashisht Hot Springs Valley Lodge": "photo-1518780664697-55e3ad937233",

    # 6. Varanasi (6 hotels)
    "Ganges Riverfront Heritage Haveli (Demo)": "photo-1522708323590-d24dbb6b0267",
    "BrijRama Palace Heritage Ghat Hotel": "photo-1505691938895-1758d7feb511",
    "Dashashwamedh Aarti View Guesthouse": "photo-1502672260266-1c1ef2d93688",
    "Sarnath Peaceful Retreat & Spa": "photo-1544984243-ec57ea16fe25",
    "Kashi Vishwanath Golden Temple Stay": "photo-1555854877-bab0e564b8d5",
    "Assi Riverside Boutique Inn": "photo-1513694203232-719a280e022f",

    # 7. Kerala (6 hotels)
    "Coconut Lagoon Backwater Retreat (Demo)": "photo-1563911302283-d2bc129e7570",
    "Kumarakom Lakefront Palace Resort": "photo-1580587771525-78b9dba3b914",
    "Munnar Misty Tea Hills Bungalow": "photo-1501785888041-af3ef285b470",
    "Alleppey Backwater Houseboat Stay": "photo-1576013551627-0cc20b96c2a7",
    "Fort Kochi Colonial Heritage Inn": "photo-1512915922686-57c11dde9b6b",
    "Varkala Cliff Oceanview Resort": "photo-1529290130-4ca3753253ae",

    # 8. Tamil Nadu (6 hotels)
    "Shore Temple Heritage Resort (Demo)": "photo-1506929562872-bb421503ef21",
    "Madurai Meenakshi Royal Palace Hotel": "photo-1512918728675-ed5a9ecdebfd",
    "Thanjavur Chola Heritage Haven": "photo-1513584684374-8bab748fbf90",
    "Rameswaram Oceanfront Pilgrim Stay": "photo-1505693416388-ac5ce068fe85",
    "Kodaikanal Pine Mist Mountain Lodge": "photo-1516455590571-18256e5bb9ff",
    "Kanyakumari Sunset & Sunrise Grand": "photo-1499793983690-e29da59ef1c2",

    # 9. Delhi (6 hotels)
    "The Imperial Grand Residency (Demo)": "photo-1561501900-3701fa6a0864",
    "The Leela Palace Chanakyapuri": "photo-1591825729269-caeb344f6df2",
    "Connaught Place Heritage Boutique Stay": "photo-1560448204-e02f11c3d0e2",
    "Chandni Chowk Haveli Heritage Inn": "photo-1554995207-c18c203602cb",
    "Aerocity Transit Grand Suites": "photo-1586611292717-f828b167408c",
    "Hauz Khas Village Bohemian Guesthouse": "photo-1504674900247-0877df9cc836",

    # 10. Agra (6 hotels)
    "Taj View Haveli & Gardens (Demo)": "photo-1562778612-e1e0cda9915c",
    "The Oberoi Amarvilas Royal Stay": "photo-1590490359683-658d3d23f972",
    "Fatehabad Heritage Royal Court": "photo-1613490493576-7fde63acd811",
    "Tajganj Budget Rooftop Inn": "photo-1522771739844-6a9f6d5f14af",
    "Agra Fort Colonial Residency": "photo-1502005229762-ee1b2da9730f",
    "Mehtab Bagh Riverside Garden Retreat": "photo-1560185007-cde436f6a4d0",

    # 11. Rishikesh (6 hotels)
    "Ganga Bliss Riverside Sanctuary (Demo)": "photo-1540555700478-4be289fbecef",
    "Ananda Foothills Wellness Resort": "photo-1506126613408-eca07ce68773",
    "Tapovan Riverview Yoga Retreat": "photo-1478131143081-80f7f84ca84d",
    "Lakshman Jhula Bohemian Riverside Inn": "photo-1560185008-b033106af5c3",
    "Shivpuri Himalayan Adventure Camp & Resort": "photo-1560185127-6ed189bf02f4",
    "Parmarth Ghat Spiritual Residency": "photo-1584622650111-993a426fbf0a",

    # 12. Jaipur (6 hotels)
    "Pink City Royal Haveli & Spa (Demo)": "photo-1574643156929-51fa098b0394",
    "Rambagh Palace Heritage Grandeur": "photo-1584132915807-fd1f5fbc078f",
    "Hawa Mahal Heritage Palace Inn": "photo-1595526114035-0d45ed16cfbf",
    "Amer Fort Valley View Resort": "photo-1598928506311-c55ded91a20c",
    "MI Road Central Business Grand": "photo-1616486338812-3dadae4b4ace",
    "Jal Mahal Lake Breeze Retreat": "photo-1616046229478-9901c5536a45",

    # 13. Mumbai (6 hotels)
    "Marine Drive Promenade Residency (Demo)": "photo-1616594039964-ae9021a400a0",
    "The Taj Mahal Palace Colaba": "photo-1570168007204-dfb528c6958f",
    "Juhu Beach Sunset Boulevard Resort": "photo-1617859047452-8510bcf207fd",
    "Bandra West Bohemian Art Boutique": "photo-1615874959474-d609969a20ed",
    "Fort Heritage Colonial Inn": "photo-1615873968403-89e068629265",
    "Powai Lake Luxury Business Haven": "photo-1615876234886-fd9a39fa979b",

    # 14. Bengaluru (6 hotels)
    "Garden City Palms Hotel (Demo)": "photo-1600585154340-be6161a56a0c",
    "The Leela Palace Old Airport Road": "photo-1600596542815-ffad4c1539a9",
    "Indiranagar Urban Boutique Stay": "photo-1600607687939-ce8a6c25118c",
    "Cubbon Park Green Oasis Hotel": "photo-1600607687920-4e2a09cf159d",
    "Koramangala Tech Hub Inn": "photo-1600565193348-f74bd3c7ccdf",
    "Whitefield IT Expressway Suites": "photo-1600585154526-990dced4db0d",

    # 15. Mysuru (6 hotels)
    "Royal Mysore Palace Heritage Stay (Demo)": "photo-1600573472591-ee6b68d14c68",
    "Lalitha Mahal Palace Hotel": "photo-1600566753190-17f0baa2a6c3",
    "Chamundi Hill Serenity Resort": "photo-1600566753086-00f18fb6b3ea",
    "Devaraja Market Heritage Inn": "photo-1600566753376-12c8ab7fb75b",
    "Brindavan Garden Waterside Resort": "photo-1600585152220-90363fe7e115",
    "Mysore Palace Gateway Court": "photo-1600585154363-67eb9e2e2099",
}

print(f"Total hotels mapped: {len(HOTEL_UNIQUE_IDS)}")
print(f"Unique hotel photo IDs: {len(set(HOTEL_UNIQUE_IDS.values()))}")
assert len(HOTEL_UNIQUE_IDS) == len(set(HOTEL_UNIQUE_IDS.values())), "Duplicates found in HOTEL_UNIQUE_IDS!"
print("SUCCESS: 100% of all 91 hotels have completely unique photo IDs!")

