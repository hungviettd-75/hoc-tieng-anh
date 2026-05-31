# Mẫu sinh từ vựng chuẩn cho A1-C1 của 6 chủ đề chính:
# travel, tech, ai, marketing, job, business

import json
import sqlite3
import re
import eng_to_ipa as ipa_lib

# Load existing words to avoid duplicate
with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/existing_words.json', 'r', encoding='utf-8') as f:
    existing_map = json.load(f)

# Từ điển thô chứa bộ từ vựng phong phú tự động lọc bỏ các từ trùng lắp
# Mỗi chủ đề/level cần có đúng 50 từ.

# 1. TRAVEL
travel_pool = {
    "A1": [
        ("Go", "/ɡəʊ/", "Đi, di chuyển", "I want to go to London."),
        ("City", "/ˈsɪt.i/", "Thành phố", "Paris is a beautiful city."),
        ("Map", "/mæp/", "Bản đồ", "We bought a city map."),
        ("Train", "/treɪn/", "Tàu hỏa", "The train arrives at ten."),
        ("Plane", "/pleɪn/", "Máy bay", "The plane flies very high."),
        ("Car", "/kɑːr/", "Xe ô tô", "We rented a small car."),
        ("Road", "/rəʊd/", "Con đường", "The road is very long."),
        ("Room", "/ruːm/", "Căn phòng, phòng nghỉ", "My room is on the second floor."),
        ("Stop", "/stɒp/", "Điểm dừng, trạm dừng", "Get off at the next bus stop."),
        ("Land", "/lænd/", "Đất liền, vùng đất", "They saw land after weeks at sea."),
        ("Lake", "/leɪk/", "Hồ nước", "We walked around the lake."),
        ("Park", "/pɑːk/", "Công viên", "The park is full of flowers."),
        ("Shop", "/ʃɒp/", "Cửa hàng", "I need to find a gift shop."),
        ("Street", "/striːt/", "Đường phố", "This street is very quiet."),
        ("Time", "/taɪm/", "Thời gian, giờ giấc", "What time does the tour start?"),
        ("Boat", "/bəʊt/", "Thuyền, tàu nhỏ", "They took a small boat to the island."),
        ("Port", "/pɔːt/", "Cảng, hải cảng", "The ship docked at the port."),
        ("Day", "/deɪ/", "Ngày, ban ngày", "It is a sunny day for travel."),
        ("Night", "/naɪt/", "Đêm, ban đêm", "We stayed at the hotel for one night."),
        ("Year", "/jɪər/", "Năm", "They travel abroad once a year."),
        ("Holiday", "/ˈhɒl.ə.deɪ/", "Ngày nghỉ, kỳ nghỉ", "We are on holiday this week."),
        ("Place", "/pleɪs/", "Địa điểm, nơi chốn", "This is a great place to visit."),
        ("World", "/wɜːld/", "Thế giới", "I want to travel the world."),
        ("Country", "/ˈkʌn.tri/", "Đất nước, quốc gia", "Japan is a safe country to visit."),
        ("Town", "/taʊn/", "Thị trấn", "The town is very old and small."),
        ("Sea", "/siː/", "Biển, đại dương", "The sea is warm today."),
        ("Forest", "/ˈfɒr.ɪst/", "Khu rừng", "We hiked in the deep forest."),
        ("Hill", "/hɪl/", "Đồi, ngọn đồi", "They climbed to the top of the hill."),
        ("River", "/ˈrɪv.ər/", "Dòng sông", "A river flows through the city."),
        ("Island", "/ˈaɪ.lənd/", "Hòn đảo", "We spent the summer on a tropical island."),
        ("Key", "/kiː/", "Chìa khóa", "Here is the key to your room."),
        ("Door", "/dɔːr/", "Cửa, cánh cửa", "Please lock the door behind you."),
        ("Luggage", "/ˈlʌɡ.ɪdʒ/", "Hành lý", "I carried my heavy luggage to the car."),
        ("Guide", "/ɡaɪd/", "Hướng dẫn viên; sách chỉ dẫn", "The guide showed us the museum."),
        ("Hostel", "/ˈhɒs.təl/", "Nhà nghỉ giá rẻ", "Hostels are great for budget travelers."),
        ("Station", "/ˈsteɪ.ʃən/", "Nhà ga, trạm", "Meet me at the train station."),
        ("Flight", "/flaɪt/", "Chuyến bay", "Our flight is delayed by an hour."),
        ("Passport", "/ˈpɑːs.pɔːt/", "Hộ chiếu", "You need a passport to travel abroad."),
        ("Ticket", "/ˈtɪk.ɪt/", "Vé", "Show your ticket to the driver."),
        ("Hotel", "/həʊˈtel/", "Khách sạn", "We booked a room at the hotel."),
        ("Bus", "/bʌs/", "Xe buýt", "I take the bus every morning."),
        ("Bag", "/bæɡ/", "Túi xách, ba lô", "Put your water bottle in your bag."),
        ("Beach", "/biːtʃ/", "Bãi biển", "We sat on the sandy beach."),
        ("Fly", "/flaɪ/", "Bay, đi máy bay", "Birds fly south for the winter."),
        ("Visa", "/ˈviː.zə/", "Thị thực nhập cảnh", "She applied for a student visa."),
        ("Inn", "/ɪn/", "Nhà trọ cổ", "The travelers stayed at a cozy inn."),
        ("Traveler", "/ˈtræv.əl.ər/", "Khách lữ hành", "The traveler rested by the road."),
        ("Booking", "/ˈbʊk.ɪŋ/", "Việc đặt trước", "Please check your booking details."),
        ("Lodging", "/ˈlɒdʒ.ɪŋ/", "Chỗ trọ, nơi lưu trú", "They searched for cheap lodging."),
        ("Attraction", "/əˈtræk.ʃən/", "Điểm tham quan hấp dẫn", "The palace is a popular tourist attraction.")
    ]
}
