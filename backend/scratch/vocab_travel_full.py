import json
import sqlite3
import sys
import os

# Set sys.path so we can import DB modules
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import SessionLocal
from app.models.models import Vocabulary

# Chúng ta định nghĩa các bộ từ vựng cực kỳ phong phú và không trùng lặp cho các chủ đề:
# ai, travel, tech, marketing, job, business

# Bộ từ chuẩn 50 từ cho mỗi level x 6 chủ đề = 30 level-topics khác nhau
# Tránh tuyệt đối trùng với existing_words.json

with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/existing_words.json', 'r', encoding='utf-8') as f:
    existing_map = json.load(f)

existing_words_set = set(k.lower().strip() for k in existing_map.keys())

VOCABULARY_DATA = {
    "travel": {
        "A1": [
            ("map", "/mæp/", "bản đồ", "We bought a city map."),
            ("train", "/treɪn/", "tàu hỏa", "The train arrives at ten."),
            ("plane", "/pleɪn/", "máy bay", "The plane flies very high."),
            ("car", "/kɑːr/", "xe ô tô", "We rented a small car."),
            ("road", "/rəʊd/", "con đường", "The road is very long."),
            ("room", "/ruːm/", "căn phòng, phòng nghỉ", "My room is on the second floor."),
            ("stop", "/stɒp/", "điểm dừng, trạm dừng", "Get off at the next bus stop."),
            ("land", "/lænd/", "đất liền, vùng đất", "They saw land after weeks at sea."),
            ("lake", "/leɪk/", "hồ nước", "We walked around the lake."),
            ("park", "/pɑːk/", "công viên", "The park is full of flowers."),
            ("shop", "/ʃɒp/", "cửa hàng", "I need to find a gift shop."),
            ("street", "/striːt/", "đường phố", "This street is very quiet."),
            ("time", "/taɪm/", "thời gian, giờ giấc", "What time does the tour start?"),
            ("boat", "/bəʊt/", "thuyền, tàu nhỏ", "They took a small boat to the island."),
            ("port", "/pɔːt/", "cảng, hải cảng", "The ship docked at the port."),
            ("day", "/deɪ/", "ngày, ban ngày", "It is a sunny day for travel."),
            ("night", "/naɪt/", "đêm, ban đêm", "We stayed at the hotel for one night."),
            ("year", "/jɪər/", "năm", "They travel abroad once a year."),
            ("holiday", "/ˈhɒl.ə.deɪ/", "ngày nghỉ, kỳ nghỉ", "We are on holiday this week."),
            ("place", "/pleɪs/", "địa điểm, nơi chốn", "This is a great place to visit."),
            ("world", "/wɜːld/", "thế giới", "I want to travel the world."),
            ("country", "/ˈkʌn.tri/", "đất nước, quốc gia", "Japan is a safe country to visit."),
            ("town", "/taʊn/", "thị trấn", "The town is very old and small."),
            ("sea", "/siː/", "biển, đại dương", "The sea is warm today."),
            ("forest", "/ˈfɒr.ɪst/", "khu rừng", "We hiked in the deep forest."),
            ("hill", "/hɪl/", "đồi, ngọn đồi", "They climbed to the top of the hill."),
            ("river", "/ˈrɪv.ər/", "dòng sông", "A river flows through the city."),
            ("island", "/ˈaɪ.lənd/", "hòn đảo", "We spent the summer on a tropical island."),
            ("key", "/kiː/", "chìa khóa", "Here is the key to your room."),
            ("door", "/dɔːr/", "cửa, cánh cửa", "Please lock the door behind you."),
            ("bag", "/bæɡ/", "túi xách, ba lô", "Put your water bottle in your bag."),
            ("ticket", "/ˈtɪk.ɪt/", "vé", "Show your ticket to the driver."),
            ("hotel", "/həʊˈtel/", "khách sạn", "We booked a room at the hotel."),
            ("bus", "/bʌs/", "xe buýt", "I take the bus every morning."),
            ("passport", "/ˈpɑːs.pɔːt/", "hộ chiếu", "You need a passport to travel abroad."),
            ("flight", "/flaɪt/", "chuyến bay", "Our flight is delayed by an hour."),
            ("station", "/ˈsteɪ.ʃən/", "nhà ga, trạm", "Meet me at the train station."),
            ("guide", "/ɡaɪd/", "hướng dẫn viên; sách chỉ dẫn", "The guide showed us the museum."),
            ("hostel", "/ˈhɒs.təl/", "nhà nghỉ giá rẻ", "Hostels are great for budget travelers."),
            ("luggage", "/ˈlʌɡ.ɪdʒ/", "hành lý du lịch", "You can leave your heavy luggage at the hotel reception."),
            ("beach", "/biːtʃ/", "bãi biển", "We sat on the sandy beach."),
            ("fly", "/flaɪ/", "bay, đi máy bay", "Birds fly south for the winter."),
            ("visa", "/ˈviː.zə/", "thị thực nhập cảnh", "She applied for a student visa."),
            ("inn", "/ɪn/", "nhà trọ cổ", "The travelers stayed at a cozy inn."),
            ("traveler", "/ˈtræv.əl.ər/", "khách lữ hành", "The traveler rested by the road."),
            ("booking", "/ˈbʊk.ɪŋ/", "việc đặt trước", "Please check your booking details."),
            ("lodging", "/ˈlɒdʒ.ɪŋ/", "chỗ trọ, nơi lưu trú tạm", "They searched for cheap lodging."),
            ("attraction", "/əˈtræk.ʃən/", "điểm tham quan hấp dẫn", "The palace is a popular tourist attraction."),
            ("pass", "/pɑːs/", "thẻ thông hành, thẻ ra vào", "Show your boarding pass at the gate."),
            ("coach", "/kəʊtʃ/", "xe khách liên tỉnh", "We took a coach to the next city.")
        ],
        "A2": [
            ("airport", "/ˈeə.pɔːt/", "sân bay", "The airport is far from the city."),
            ("luggage scale", "/ˈlʌɡ.ɪdʒ skeɪl/", "cân hành lý", "We weighed our bags on the scale."),
            ("boarding gate", "/ˈbɔː.dɪŋ ɡeɪt/", "cổng lên máy bay", "Proceed to boarding gate seven."),
            ("passenger train", "/ˈpæs.ən.dʒər treɪn/", "tàu chở khách", "The passenger train runs hourly."),
            ("timetable", "/ˈtaɪm.teɪ.bəl/", "lịch chạy tàu/xe", "Check the train timetable online."),
            ("taxi", "/ˈtæk.si/", "xe taxi", "We hailed a taxi outside the station."),
            ("subway", "/ˈsʌb.weɪ/", "tàu điện ngầm", "The subway is fast and cheap."),
            ("highway", "/ˈhaɪ.weɪ/", "đường cao tốc", "Cars sped down the highway."),
            ("journey time", "/ˈdʒɜː.ni taɪm/", "thời gian di chuyển", "The journey time is three hours."),
            ("ticket office", "/ˈtɪk.ɪt ˈɒf.ɪs/", "phòng vé", "Buy your tickets at the ticket office."),
            ("reservation desk", "/ˌrez.əˈveɪ.ʃən dɛsk/", "quầy đặt chỗ trước", "Ask at the reservation desk."),
            ("platform", "/ˈplæt.fɔːm/", "sân ga, thềm ga", "The train is on platform four."),
            ("passenger boat", "/ˈpæs.ən.dʒər bəʊt/", "tàu chở khách đường thủy", "The boat crossed the calm river."),
            ("harbor", "/ˈhɑː.bər/", "bến cảng, vũng tàu", "Yachts docked in the peaceful harbor."),
            ("cruise", "/kruːz/", "chuyến du thuyền", "They took a cruise in the Caribbean."),
            ("cabin", "/ˈkæb.ɪn/", "cabin, buồng ngủ trên tàu", "Our cabin was very comfortable."),
            ("backpacker", "/ˈbæk.pæk.ər/", "khách du lịch ba lô", "The backpacker carried a large tent."),
            ("souvenir", "/ˌsuː.vənˈɪər/", "quà lưu niệm", "She bought a souvenir in Paris."),
            ("sightseeing bus", "/ˈsaɪtˌsiː.ɪŋ bʌs/", "xe buýt ngắm cảnh", "We took an open-top sightseeing bus."),
            ("foreign country", "/ˈfɒr.ən ˈkʌn.tri/", "nước ngoài", "He loves visiting foreign countries."),
            ("tour guide", "/tʊər ɡaɪd/", "hướng dẫn viên du lịch", "The tour guide explained the history."),
            ("local food", "/ˈləʊ.kəl fuːd/", "món ăn địa phương", "We tried some delicious local food."),
            ("market stall", "/ˈmɑː.kɪt stɔːl/", "quầy hàng ở chợ", "She bought fresh fruit from a market stall."),
            ("national park", "/ˈnæʃ.ən.əl pɑːk/", "vườn quốc gia", "They camped in the national park."),
            ("hiking trail", "/ˈhaɪ.kɪŋ treɪl/", "đường mòn đi bộ dã ngoại", "Follow the marked hiking trail."),
            ("waterfall", "/ˈwɔː.tə.fɔːl/", "thác nước", "The waterfall is high and beautiful."),
            ("mountain peak", "/ˈmaʊn.tɪn piːk/", "đỉnh núi", "Snow covered the mountain peak."),
            ("canyon", "/ˈkæn.jən/", "hẻm núi lớn", "They hiked down into the deep canyon."),
            ("desert", "/ˈdez.ət/", "sa mạc", "Cacti grow in the hot desert."),
            ("beach resort", "/biːtʃ rɪˈzɔːt/", "khu nghỉ dưỡng bãi biển", "We booked a room at a beach resort."),
            ("swimming pool", "/ˈswɪm.ɪŋ puːl/", "bể bơi", "The hotel has an outdoor swimming pool."),
            ("seafood", "/ˈsiː.fuːd/", "hải sản", "They serve fresh seafood by the harbor."),
            ("umbrella", "/ʌmˈbrel.ə/", "cái ô, cái dù", "Take an umbrella in case it rains."),
            ("sunscreen", "/ˈsʌn.skriːn/", "kem chống nắng", "Apply sunscreen before going to the beach."),
            ("sunglasses", "/ˈsʌn.ɡlɑː.sɪz/", "kính râm, kính mát", "She wore dark sunglasses in the sun."),
            ("camera lens", "/ˈkæm.ər.ə lenz/", "ống kính máy ảnh", "Clean your camera lens regularly."),
            ("photo album", "/ˈfəʊ.təʊ ˈæl.bəm/", "cuốn album ảnh", "She put the holiday photos in an album."),
            ("postcard", "/ˈpəʊst.kɑːd/", "bưu thiếp", "Send a postcard to your family."),
            ("luggage tag", "/ˈlʌɡ.ɪdʒ tæɡ/", "thẻ ghi thông tin hành lý", "Write your name on the luggage tag."),
            ("backpack", "/ˈbæk.pæk/", "ba lô", "He packed his clothes into a backpack."),
            ("sleeping bag", "/ˈsliː.pɪŋ bæɡ/", "túi ngủ dã ngoại", "It got cold in the sleeping bag."),
            ("tent", "/tent/", "cái lều dã ngoại", "We set up our tent under the trees."),
            ("camping site", "/ˈkæm.pɪŋ saɪt/", "bãi cắm trại", "The camping site has hot showers."),
            ("travel agency", "/ˈtræv.əl ˈeɪ.dʒən.si/", "đại lý du lịch", "Book the tour through a travel agency."),
            ("map guide", "/mæp ɡaɪd/", "bản đồ chỉ dẫn", "The map guide shows historical sites."),
            ("information desk", "/ˌɪn.fəˈmeɪ.ʃən dɛsk/", "quầy thông tin", "Ask for a free map at the information desk."),
            ("currency", "/ˈkʌr.ən.si/", "tiền tệ", "Exchange your money for local currency."),
            ("exchange rate", "/ɪksˈtʃeɪndʒ reɪt/", "tỷ giá hối đoái", "The exchange rate is good today."),
            ("cash machine", "/kæʃ məˈʃiːn/", "máy rút tiền tự động ATM", "I need to find a cash machine."),
            ("credit card", "/ˈkred.ɪt kɑːd/", "thẻ tín dụng", "Can I pay by credit card?")
        ]
    }
}
