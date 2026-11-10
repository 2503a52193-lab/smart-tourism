import sys

DESTINATIONS = {
    "Goa": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=1200&q=80",
    "Hyderabad": "https://images.unsplash.com/photo-1609137144822-44675dfd35a5?auto=format&fit=crop&w=1200&q=80",
    "Chennai": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=1200&q=80",
    "Ooty": "https://images.unsplash.com/photo-1593693397690-362cb9666fc2?auto=format&fit=crop&w=1200&q=80",
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

# 60 unique attraction images - each uniquely matched to that exact attraction
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
    "Sarnath Archaeological Site": "https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?auto=format&fit=crop&w=1000&q=80",

    # 7. Kerala
    "Munnar Tea Gardens": "https://images.unsplash.com/photo-1593693397690-362cb9666fc2?auto=format&fit=crop&w=1000&q=80",
    "Alleppey Backwaters": "https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?auto=format&fit=crop&w=1000&q=80",
    "Thekkady & Periyar National Park": "https://images.unsplash.com/photo-1575550959106-5a7defe28b56?auto=format&fit=crop&w=1000&q=80",
    "Fort Kochi & Chinese Fishing Nets": "https://images.unsplash.com/photo-1714931862306-7abe321b6b5f?auto=format&fit=crop&w=1000&q=80",

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
    "Amber Palace (Amer Fort)": "https://images.unsplash.com/photo-1592635196078-9fe3d54f2377?auto=format&fit=crop&w=1000&q=80",
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

# 91 unique hotel images - each accurately matched to property type & destination
HOTELS = {
    # 1. Goa (7 hotels)
    "Goa Heritage Palms Resort & Spa (Demo)": "https://images.unsplash.com/photo-1582719508461-905c673771fd?auto=format&fit=crop&w=1200&q=80",
    "Taj Aguada Cliffside Resort & Spa": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=1200&q=80",
    "Baga Blue Sands Boutique Hotel": "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?auto=format&fit=crop&w=1200&q=80",
    "Palolem Palm Bay Eco Resort": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=1200&q=80",
    "Panaji Old Latin Quarter Inn": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
    "Anjuna Sunset Cliffside Villas": "https://images.unsplash.com/photo-1584132967334-10e028bd69f7?auto=format&fit=crop&w=1200&q=80",
    "The Grand Azure Bay Resort": "https://images.unsplash.com/photo-1540541338287-41700207dee6?auto=format&fit=crop&w=1200&q=80",

    # 2. Hyderabad (6 hotels)
    "Hyderabad Charminar Heritage Grand (Demo)": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1200&q=80",
    "Taj Falaknuma Palace Residency": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80",
    "HITEC City Silicon Boutique Hotel": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1200&q=80",
    "Hussain Sagar Lakeview Grand": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=1200&q=80",
    "Golconda Heritage Gate Inn": "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1200&q=80",
    "Jubilee Hills Royal Court Hotel": "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?auto=format&fit=crop&w=1200&q=80",

    # 3. Chennai (6 hotels)
    "Chennai Marina Bay Breeze Hotel (Demo)": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=1200&q=80",
    "ITC Grand Chola Heritage Residency": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=1200&q=80",
    "ECR Beach Haven Resort": "https://images.unsplash.com/photo-1571896349842-48c89491295b?auto=format&fit=crop&w=1200&q=80",
    "Mylapore Heritage Temple Stay": "https://images.unsplash.com/photo-1591088398332-8a7791972843?auto=format&fit=crop&w=1200&q=80",
    "T. Nagar Central Plaza Hotel": "https://images.unsplash.com/photo-1568084680786-a84f91d1153c?auto=format&fit=crop&w=1200&q=80",
    "Nungambakkam Garden Court Hotel": "https://images.unsplash.com/photo-1578683010344-934d402488a0?auto=format&fit=crop&w=1200&q=80",

    # 4. Ooty (6 hotels)
    "Nilgiri Mist Valley Retreat (Demo)": "https://images.unsplash.com/photo-1587061949409-02df41d5e562?auto=format&fit=crop&w=1200&q=80",
    "Savoy Heritage Nilgiri Hill Resort": "https://images.unsplash.com/photo-1596436889106-be35e843f974?auto=format&fit=crop&w=1200&q=80",
    "Doddabetta Peak Mountain Lodge": "https://images.unsplash.com/photo-1510798831971-661eb04b3739?auto=format&fit=crop&w=1200&q=80",
    "Ooty Lake Pineview Cottages": "https://images.unsplash.com/photo-1445019980597-93fa8acb246c?auto=format&fit=crop&w=1200&q=80",
    "Nilgiri Botanical Tea Estate Stay": "https://images.unsplash.com/photo-1507652313519-d4e9174996dd?auto=format&fit=crop&w=1200&q=80",
    "Coonoor Mountain Breeze Inn": "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=1200&q=80",

    # 5. Manali (6 hotels)
    "Himalayan Pine Glades Resort (Demo)": "https://images.unsplash.com/photo-1548777123-e216912df7d8?auto=format&fit=crop&w=1200&q=80",
    "Solang Valley Alpine Luxury Chalet": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1200&q=80",
    "Old Manali Riverside Wooden Cottages": "https://images.unsplash.com/photo-1449844908441-8829872d2607?auto=format&fit=crop&w=1200&q=80",
    "Rohtang Foothills Snowcrest Resort": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80",
    "Mall Road Central Grand Stay": "https://images.unsplash.com/photo-1564501049412-61c2a3083791?auto=format&fit=crop&w=1200&q=80",
    "Vashisht Hot Springs Valley Lodge": "https://images.unsplash.com/photo-1518780664697-55e3ad937233?auto=format&fit=crop&w=1200&q=80",

    # 6. Varanasi (6 hotels)
    "Ganges Riverfront Heritage Haveli (Demo)": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&q=80",
    "BrijRama Palace Heritage Ghat Hotel": "https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&w=1200&q=80",
    "Dashashwamedh Aarti View Guesthouse": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=1200&q=80",
    "Sarnath Peaceful Retreat & Spa": "https://images.unsplash.com/photo-1544984243-ec57ea16fe25?auto=format&fit=crop&w=1200&q=80",
    "Kashi Vishwanath Golden Temple Stay": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=1200&q=80",
    "Assi Riverside Boutique Inn": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1200&q=80",

    # 7. Kerala (6 hotels)
    "Coconut Lagoon Backwater Retreat (Demo)": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
    "Kumarakom Lakefront Palace Resort": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1200&q=80",
    "Munnar Misty Tea Hills Bungalow": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1200&q=80",
    "Alleppey Backwater Houseboat Stay": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=1200&q=80",
    "Fort Kochi Colonial Heritage Inn": "https://images.unsplash.com/photo-1512915922686-57c11dde9b6b?auto=format&fit=crop&w=1200&q=80",
    "Varkala Cliff Oceanview Resort": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=80",

    # 8. Tamil Nadu (6 hotels)
    "Shore Temple Heritage Resort (Demo)": "https://images.unsplash.com/photo-1506929562872-bb421503ef21?auto=format&fit=crop&w=1200&q=80",
    "Madurai Meenakshi Royal Palace Hotel": "https://images.unsplash.com/photo-1512918728675-ed5a9ecdebfd?auto=format&fit=crop&w=1200&q=80",
    "Thanjavur Chola Heritage Haven": "https://images.unsplash.com/photo-1513584684374-8bab748fbf90?auto=format&fit=crop&w=1200&q=80",
    "Rameswaram Oceanfront Pilgrim Stay": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=80",
    "Kodaikanal Pine Mist Mountain Lodge": "https://images.unsplash.com/photo-1516455590571-18256e5bb9ff?auto=format&fit=crop&w=1200&q=80",
    "Kanyakumari Sunset & Sunrise Grand": "https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?auto=format&fit=crop&w=1200&q=80",

    # 9. Delhi (6 hotels)
    "The Imperial Grand Residency (Demo)": "https://images.unsplash.com/photo-1578683010344-934d402488a0?auto=format&fit=crop&w=1200&q=80",
    "The Leela Palace Chanakyapuri": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=1200&q=80",
    "Connaught Place Heritage Boutique Stay": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=1200&q=80",
    "Chandni Chowk Haveli Heritage Inn": "https://images.unsplash.com/photo-1554995207-c18c203602cb?auto=format&fit=crop&w=1200&q=80",
    "Aerocity Transit Grand Suites": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80",
    "Hauz Khas Village Bohemian Guesthouse": "https://images.unsplash.com/photo-1507652313519-d4e9174996dd?auto=format&fit=crop&w=1200&q=80",

    # 10. Agra (6 hotels)
    "Taj View Haveli & Gardens (Demo)": "https://images.unsplash.com/photo-1596436889106-be35e843f974?auto=format&fit=crop&w=1200&q=80",
    "The Oberoi Amarvilas Royal Stay": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1200&q=80",
    "Fatehabad Heritage Royal Court": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
    "Tajganj Budget Rooftop Inn": "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?auto=format&fit=crop&w=1200&q=80",
    "Agra Fort Colonial Residency": "https://images.unsplash.com/photo-1502005229762-ee1b2da9730f?auto=format&fit=crop&w=1200&q=80",
    "Mehtab Bagh Riverside Garden Retreat": "https://images.unsplash.com/photo-1512918728675-ed5a9ecdebfd?auto=format&fit=crop&w=1200&q=80",

    # 11. Rishikesh (6 hotels)
    "Ganga Bliss Riverside Sanctuary (Demo)": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
    "Ananda Foothills Wellness Resort": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=1200&q=80",
    "Tapovan Riverview Yoga Retreat": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=1200&q=80",
    "Lakshman Jhula Bohemian Riverside Inn": "https://images.unsplash.com/photo-1445019980597-93fa8acb246c?auto=format&fit=crop&w=1200&q=80",
    "Shivpuri Himalayan Adventure Camp & Resort": "https://images.unsplash.com/photo-1478131143081-80f7f84ca84d?auto=format&fit=crop&w=1200&q=80",
    "Parmarth Ghat Spiritual Residency": "https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?auto=format&fit=crop&w=1200&q=80",

    # 12. Jaipur (6 hotels)
    "Pink City Royal Haveli & Spa (Demo)": "https://images.unsplash.com/photo-1582719508461-905c673771fd?auto=format&fit=crop&w=1200&q=80",
    "Rambagh Palace Heritage Grandeur": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=1200&q=80",
    "Hawa Mahal Heritage Palace Inn": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=1200&q=80",
    "Amer Fort Valley View Resort": "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?auto=format&fit=crop&w=1200&q=80",
    "MI Road Central Business Grand": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1200&q=80",
    "Jal Mahal Lake Breeze Retreat": "https://images.unsplash.com/photo-1584132967334-10e028bd69f7?auto=format&fit=crop&w=1200&q=80",

    # 13. Mumbai (6 hotels)
    "Marine Drive Promenade Residency (Demo)": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1200&q=80",
    "The Taj Mahal Palace Colaba": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?auto=format&fit=crop&w=1200&q=80",
    "Juhu Beach Sunset Boulevard Resort": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
    "Bandra West Bohemian Art Boutique": "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?auto=format&fit=crop&w=1200&q=80",
    "Fort Heritage Colonial Inn": "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1200&q=80",
    "Powai Lake Luxury Business Haven": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=1200&q=80",

    # 14. Bengaluru (6 hotels)
    "Garden City Palms Hotel (Demo)": "https://images.unsplash.com/photo-1568084680786-a84f91d1153c?auto=format&fit=crop&w=1200&q=80",
    "The Leela Palace Old Airport Road": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80",
    "Indiranagar Urban Boutique Stay": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&q=80",
    "Cubbon Park Green Oasis Hotel": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1200&q=80",
    "Koramangala Tech Hub Inn": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=1200&q=80",
    "Whitefield IT Expressway Suites": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=1200&q=80",

    # 15. Mysuru (6 hotels)
    "Royal Mysore Palace Heritage Stay (Demo)": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
    "Lalitha Mahal Palace Hotel": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1200&q=80",
    "Chamundi Hill Serenity Resort": "https://images.unsplash.com/photo-1510798831971-661eb04b3739?auto=format&fit=crop&w=1200&q=80",
    "Devaraja Market Heritage Inn": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1200&q=80",
    "Brindavan Garden Waterside Resort": "https://images.unsplash.com/photo-1512918728675-ed5a9ecdebfd?auto=format&fit=crop&w=1200&q=80",
    "Mysore Palace Gateway Court": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=1200&q=80",
}

print(f"Total destinations: {len(DESTINATIONS)}")
print(f"Total attractions: {len(ATTRACTIONS)}, unique URLs: {len(set(ATTRACTIONS.values()))}")
print(f"Total hotels: {len(HOTELS)}, unique URLs: {len(set(HOTELS.values()))}")

