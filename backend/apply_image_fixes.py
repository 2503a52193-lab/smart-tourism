import sqlite3
import os
import re

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "tourism_local.db")

DESTINATIONS = {
    "Goa": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=1200&q=80",
    "Hyderabad": "https://images.unsplash.com/photo-1609137144822-44675dfd35a5?auto=format&fit=crop&w=1200&q=80",
    "Chennai": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=1200&q=80",
    "Ooty": "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?auto=format&fit=crop&w=1200&q=80",
    "Manali": "https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?auto=format&fit=crop&w=1200&q=80",
    "Varanasi": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?auto=format&fit=crop&w=1200&q=80",
    "Kerala": "https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?auto=format&fit=crop&w=1200&q=80",
    "Tamil Nadu": "https://images.unsplash.com/photo-1609766857329-8738520268ec?auto=format&fit=crop&w=1200&q=80",
    "Delhi": "https://images.unsplash.com/photo-1587474260584-136574528ed5?auto=format&fit=crop&w=1200&q=80",
    "Agra": "https://images.unsplash.com/photo-1564507592333-c60657eea523?auto=format&fit=crop&w=1200&q=80",
    "Rishikesh": "https://images.unsplash.com/photo-1595815771614-ade9d652a65d?auto=format&fit=crop&w=1200&q=80",
    "Jaipur": "https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?auto=format&fit=crop&w=1200&q=80",
    "Mumbai": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?auto=format&fit=crop&w=1200&q=80",
    "Bengaluru": "https://images.unsplash.com/photo-1596176530529-78163a4f7af2?auto=format&fit=crop&w=1200&q=80",
    "Mysuru": "https://images.unsplash.com/photo-1600100397608-f010f443b71a?auto=format&fit=crop&w=1200&q=80",
}

# 60 unique attraction images - 0 duplicates
ATTRACTIONS = {
    # 1. Goa
    "Baga Beach": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1000&q=80",
    "Calangute Beach": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=1000&q=80",
    "Fort Aguada": "https://images.unsplash.com/photo-1587974928442-77dc3e0dba72?auto=format&fit=crop&w=1000&q=80",
    "Basilica of Bom Jesus": "https://images.unsplash.com/photo-1548013146-72479768bbaa?auto=format&fit=crop&w=1000&q=80",

    # 2. Hyderabad
    "Charminar": "https://images.unsplash.com/photo-1609137144822-44675dfd35a5?auto=format&fit=crop&w=1000&q=80",
    "Golconda Fort": "https://images.unsplash.com/photo-1627894483216-2138af692e32?auto=format&fit=crop&w=1000&q=80",
    "Salar Jung Museum": "https://images.unsplash.com/photo-1565008447742-97f6f38c985c?auto=format&fit=crop&w=1000&q=80",
    "Hussain Sagar & Buddha Statue": "https://images.unsplash.com/photo-1589182373726-e4f658ab50f0?auto=format&fit=crop&w=1000&q=80",

    # 3. Chennai
    "Marina Beach": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=1000&q=80",
    "Kapaleeshwarar Temple": "https://images.unsplash.com/photo-1609766857329-8738520268ec?auto=format&fit=crop&w=1000&q=80",
    "Fort St. George": "https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=1000&q=80",
    "Government Museum Chennai": "https://images.unsplash.com/photo-1582555172866-f73bb12a2ab3?auto=format&fit=crop&w=1000&q=80",

    # 4. Ooty
    "Ooty Lake & Boathouse": "https://images.unsplash.com/photo-1498855926480-d98e83099315?auto=format&fit=crop&w=1000&q=80",
    "Government Botanical Garden": "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=1000&q=80",
    "Doddabetta Peak": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1000&q=80",
    "Government Rose Garden": "https://images.unsplash.com/photo-1496062031456-07b8f162a322?auto=format&fit=crop&w=1000&q=80",

    # 5. Manali
    "Solang Valley": "https://images.unsplash.com/photo-1579619569702-865619889797?auto=format&fit=crop&w=1000&q=80",
    "Hadimba Devi Temple": "https://images.unsplash.com/photo-1605649487212-47bdab064df7?auto=format&fit=crop&w=1000&q=80",
    "Manu Temple": "https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?auto=format&fit=crop&w=1000&q=80",
    "Vashisht Hot Springs": "https://images.unsplash.com/photo-1518457607834-6e8d80c183c5?auto=format&fit=crop&w=1000&q=80",

    # 6. Varanasi
    "Dashashwamedh Ghat": "https://images.unsplash.com/photo-1571536802807-30451e3955d8?auto=format&fit=crop&w=1000&q=80",
    "Kashi Vishwanath Temple": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?auto=format&fit=crop&w=1000&q=80",
    "Assi Ghat": "https://images.unsplash.com/photo-1568454537842-d933259bb258?auto=format&fit=crop&w=1000&q=80",
    "Sarnath Archaeological Site": "https://images.unsplash.com/photo-1608889825103-eb5ed706fc64?auto=format&fit=crop&w=1000&q=80",

    # 7. Kerala
    "Munnar Tea Gardens": "https://images.unsplash.com/photo-1593693397690-362cb9666fc2?auto=format&fit=crop&w=1000&q=80",
    "Alleppey Backwaters": "https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?auto=format&fit=crop&w=1000&q=80",
    "Thekkady & Periyar National Park": "https://images.unsplash.com/photo-1575550959106-5a7defe28b56?auto=format&fit=crop&w=1000&q=80",
    "Fort Kochi": "https://images.unsplash.com/photo-1714931862306-7abe321b6b5f?auto=format&fit=crop&w=1000&q=80",

    # 8. Tamil Nadu
    "Meenakshi Amman Temple (Madurai)": "https://images.unsplash.com/photo-1692173248120-59547c3d4653?auto=format&fit=crop&w=1000&q=80",
    "Brihadeeswarar Temple (Thanjavur)": "https://images.unsplash.com/photo-1603766806347-54cdf3745953?auto=format&fit=crop&w=1000&q=80",
    "Shore Temple (Mahabalipuram)": "https://images.unsplash.com/photo-1674722758654-5b58755f81b9?auto=format&fit=crop&w=1000&q=80",
    "Dhanushkodi Beach & Ghost Town": "https://images.unsplash.com/photo-1706932642959-97cdde19ef0b?auto=format&fit=crop&w=1000&q=80",

    # 9. Delhi
    "Red Fort (Lal Qila)": "https://images.unsplash.com/photo-1598434192043-71111c1b3f41?auto=format&fit=crop&w=1000&q=80",
    "Qutub Minar": "https://images.unsplash.com/photo-1545129139-1beb780cf337?auto=format&fit=crop&w=1000&q=80",
    "Humayun's Tomb": "https://images.unsplash.com/photo-1787036810855-f10bf94f7d10?auto=format&fit=crop&w=1000&q=80",
    "India Gate & Kartavya Path": "https://images.unsplash.com/photo-1585136917195-236b33eb158a?auto=format&fit=crop&w=1000&q=80",

    # 10. Agra
    "Taj Mahal": "https://images.unsplash.com/photo-1564507592333-c60657eea523?auto=format&fit=crop&w=1000&q=80",
    "Agra Fort": "https://images.unsplash.com/photo-1665570010702-35b6ce922bdd?auto=format&fit=crop&w=1000&q=80",
    "Fatehpur Sikri": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=1000&q=80",
    "Mehtab Bagh": "https://images.unsplash.com/photo-1592635196078-9fe3d54f2377?auto=format&fit=crop&w=1000&q=80",

    # 11. Rishikesh
    "Lakshman Jhula Area": "https://images.unsplash.com/photo-1595815771614-ade9d652a65d?auto=format&fit=crop&w=1000&q=80",
    "Ram Jhula & Swarg Ashram": "https://images.unsplash.com/photo-1588096344356-9a4f6cf1a156?auto=format&fit=crop&w=1000&q=80",
    "Triveni Ghat": "https://images.unsplash.com/photo-1514565131-fce0801e5785?auto=format&fit=crop&w=1000&q=80",
    "The Beatles Ashram (Chaurasi Kutia)": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=1000&q=80",

    # 12. Jaipur
    "Amber Palace (Amer Fort)": "https://images.unsplash.com/photo-1599661046289-e31897846e41?auto=format&fit=crop&w=1000&q=80",
    "Hawa Mahal": "https://plus.unsplash.com/premium_photo-1661901647310-4deafc6f29a5?auto=format&fit=crop&w=1000&q=80",
    "City Palace Jaipur": "https://images.unsplash.com/photo-1596436889106-be35e843f974?auto=format&fit=crop&w=1000&q=80",
    "Jantar Mantar": "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=1000&q=80",

    # 13. Mumbai
    "Gateway of India": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?auto=format&fit=crop&w=1000&q=80",
    "Marine Drive Promenade": "https://images.unsplash.com/photo-1566375728060-c37e633323e3?auto=format&fit=crop&w=1000&q=80",
    "Chhatrapati Shivaji Maharaj Vastu Sangrahalaya": "https://images.unsplash.com/photo-1572947650440-e8a97ef053b2?auto=format&fit=crop&w=1000&q=80",
    "Elephanta Caves": "https://images.unsplash.com/photo-1634303771727-cf3db81e56fb?auto=format&fit=crop&w=1000&q=80",

    # 14. Bengaluru
    "Lalbagh Botanical Garden": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?auto=format&fit=crop&w=1000&q=80",
    "Bangalore Palace": "https://images.unsplash.com/photo-1596176530529-78163a4f7af2?auto=format&fit=crop&w=1000&q=80",
    "Cubbon Park & Vidhana Soudha View": "https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=1000&q=80",
    "Visvesvaraya Industrial & Technological Museum": "https://images.unsplash.com/photo-1507668077129-56e32842fceb?auto=format&fit=crop&w=1000&q=80",

    # 15. Mysuru
    "Mysore Palace (Amba Vilas)": "https://images.unsplash.com/photo-1600100397608-f010f443b71a?auto=format&fit=crop&w=1000&q=80",
    "Chamundeshwari Temple (Chamundi Hill)": "https://images.unsplash.com/photo-1714932364522-b8265c5897c2?auto=format&fit=crop&w=1000&q=80",
    "Brindavan Gardens": "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=1000&q=80",
    "Mysore Zoo (Sri Chamarajendra Zoological Gardens)": "https://images.unsplash.com/photo-1534567153574-2b12153a87f0?auto=format&fit=crop&w=1000&q=80",
}

# 91 completely distinct, property-tailored Unsplash photo IDs (0 duplicates)
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
    "Savoy Heritage Nilgiri Hill Resort": "photo-1568495248636-6432b97bd949",
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
    "The Taj Mahal Palace Colaba": "photo-1590381105924-c72589b9ef3f", # Distinct palace hotel photo
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

def update_database():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("1. Updating Destinations in DB...")
    for name, img in DESTINATIONS.items():
        c.execute("UPDATE destination SET image_url = ? WHERE name = ?", (img, name))

    print("2. Updating Attractions in DB...")
    for name, img in ATTRACTIONS.items():
        c.execute("UPDATE tourist_attraction SET image_url = ? WHERE name = ?", (img, name))

    print("3. Updating Hotels in DB...")
    for name, pid in HOTEL_UNIQUE_IDS.items():
        url = f"https://images.unsplash.com/{pid}?auto=format&fit=crop&w=1200&q=80"
        c.execute("UPDATE hotel SET image_url = ? WHERE name = ?", (url, name))

    conn.commit()
    conn.close()
    print("Database updated successfully!")

if __name__ == "__main__":
    update_database()
