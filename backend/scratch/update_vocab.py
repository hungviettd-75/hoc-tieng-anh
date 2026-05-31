import sys
import os
import json

# Them thu muc hien tai (backend) vao path de import duoc app
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import SessionLocal
from app.models.models import Vocabulary

# Danh sach cac tu thay the tuong ung
REPLACEMENTS = {
    "innovation 2": {
        "word": "breakthrough",
        "ipa": "/ˈbreɪk.θruː/",
        "meaning": "sự đột phá, bước phát triển vượt bậc",
        "example": "Scientists have made a major breakthrough in cancer research."
    },
    "bandwidth 2": {
        "word": "throughput",
        "ipa": "/ˈθruː.pʊt/",
        "meaning": "năng suất truyền dữ liệu, thông lượng",
        "example": "We need to measure the network throughput during peak hours."
    },
    "cybersecurity 2": {
        "word": "cryptography",
        "ipa": "/krɪpˈtɒɡ.rə.fi/",
        "meaning": "mật mã học",
        "example": "Cryptography is used to secure online transactions."
    },
    "cloud computing 2": {
        "word": "virtualization",
        "ipa": "/ˌvɜː.tʃu.ə.laɪˈzeɪ.ʃən/",
        "meaning": "công nghệ ảo hóa",
        "example": "Virtualization allows running multiple operating systems on one machine."
    },
    "virtual reality 2": {
        "word": "augmented reality",
        "ipa": "/ɔːɡˌmen.tɪd riˈæl.ə.ti/",
        "meaning": "thực tế tăng cường (AR)",
        "example": "Augmented reality overlays digital information onto the real world."
    },
    "wearable 2": {
        "word": "smartwatch",
        "ipa": "/ˈsmɑːt.wɒtʃ/",
        "meaning": "đồng hồ thông minh",
        "example": "His new smartwatch tracks his daily physical activity."
    },
    "streaming 2": {
        "word": "broadcasting",
        "ipa": "/ˈbrɔːd.kɑː.stɪŋ/",
        "meaning": "sự phát sóng, truyền hình",
        "example": "The broadcasting of the event was delayed by ten minutes."
    },
    "gadget 2": {
        "word": "appliance",
        "ipa": "/əˈplaɪ.əns/",
        "meaning": "thiết bị, dụng cụ gia dụng",
        "example": "Modern appliances make housework much easier."
    },
    "phone 2": {
        "word": "telephone",
        "ipa": "/ˈtel.ɪ.fəʊn/",
        "meaning": "điện thoại (nói chung/cố định)",
        "example": "Please answer the telephone if it rings."
    },
    "screen 2": {
        "word": "monitor",
        "ipa": "/ˈmɒn.ɪ.tər/",
        "meaning": "màn hình máy tính",
        "example": "She looked at the computer monitor for hours."
    },
    "camera 2": {
        "word": "webcam",
        "ipa": "/ˈweb.kæm/",
        "meaning": "máy ảnh kỹ thuật số kết nối máy tính, webcam",
        "example": "I need a new webcam for my online meetings."
    },
    "tablet 2": {
        "word": "laptop",
        "ipa": "/ˈlæp.tɒp/",
        "meaning": "máy tính xách tay",
        "example": "She opened her laptop to check her emails."
    },
    "video 2": {
        "word": "clip",
        "ipa": "/klɪp/",
        "meaning": "đoạn phim ngắn, video ngắn",
        "example": "He sent me a funny video clip yesterday."
    },
    "game 2": {
        "word": "toy",
        "ipa": "/tɔɪ/",
        "meaning": "đồ chơi",
        "example": "The child is playing with a wooden toy car."
    },
    "internet 2": {
        "word": "cyberspace",
        "ipa": "/ˈsaɪ.bə.speɪs/",
        "meaning": "không gian mạng",
        "example": "The laws protect children from online danger in cyberspace."
    },
    "email 2": {
        "word": "letter",
        "ipa": "/ˈlet.ər/",
        "meaning": "lá thư, thư tay",
        "example": "She wrote a long letter to her grandmother."
    },
    "smartphone 2": {
        "word": "cellphone",
        "ipa": "/ˈsel.fəʊn/",
        "meaning": "điện thoại di động",
        "example": "He kept his cellphone in his front pocket."
    },
    "battery 2": {
        "word": "charger",
        "ipa": "/ˈtʃɑː.dʒər/",
        "meaning": "thiết bị sạc pin",
        "example": "I left my phone charger at the office."
    },
    "download 2": {
        "word": "upload",
        "ipa": "/ʌpˈləʊd/",
        "meaning": "tải lên dữ liệu",
        "example": "It took ten minutes to upload the high-resolution photo."
    },
    "website 2": {
        "word": "webpage",
        "ipa": "/ˈweb.peɪdʒ/",
        "meaning": "trang web (một trang đơn lẻ)",
        "example": "The homepage is the first webpage you see when visiting a site."
    },
    "password 2": {
        "word": "passcode",
        "ipa": "/ˈpɑːs.kəʊd/",
        "meaning": "mật mã số",
        "example": "Enter your passcode to unlock the tablet screen."
    },
    "update 2": {
        "word": "upgrade",
        "ipa": "/ʌpˈɡreɪd/",
        "meaning": "sự nâng cấp, cải tiến",
        "example": "The software upgrade includes several new security features."
    },
    "connect 2": {
        "word": "link",
        "ipa": "/lɪŋk/",
        "meaning": "liên kết, nối liền",
        "example": "The bridge links the two islands together."
    },
    "message 2": {
        "word": "notice",
        "ipa": "/ˈnəʊ.tɪs/",
        "meaning": "thông báo, yết thị",
        "example": "There is a notice on the wall about the power outage."
    },
    "target audience 2": {
        "word": "potential customer",
        "ipa": "/pəˈten.ʃəl ˈkʌs.tə.mər/",
        "meaning": "khách hàng tiềm năng",
        "example": "We should focus our ads on potential customers in their twenties."
    },
    "campaign 2": {
        "word": "drive",
        "ipa": "/draɪv/",
        "meaning": "chiến dịch lớn, cuộc vận động",
        "example": "The government launched a drive to encourage recycling."
    },
    "branding 2": {
        "word": "identity",
        "ipa": "/aɪˈden.tə.ti/",
        "meaning": "nhận diện, danh tính thương hiệu",
        "example": "A strong corporate identity builds trust with clients."
    },
    "analytics 2": {
        "word": "statistics",
        "ipa": "/stəˈtɪs.tɪks/",
        "meaning": "số liệu thống kê",
        "example": "Official statistics show a rise in local tourism."
    },
    "conversion 2": {
        "word": "acquisition",
        "ipa": "/ˌæk.wɪˈzɪʃ.ən/",
        "meaning": "sự thu hút, thu nhận khách hàng",
        "example": "The acquisition of new clients is crucial for business growth."
    },
    "engagement 2": {
        "word": "interaction",
        "ipa": "/ˌɪn.təˈræk.ʃən/",
        "meaning": "sự tương tác qua lại",
        "example": "The classroom activities encourage interaction among students."
    },
    "influencer 2": {
        "word": "celebrity",
        "ipa": "/səˈleb.rə.ti/",
        "meaning": "người nổi tiếng",
        "example": "The movie star became an international celebrity."
    },
    "content marketing 2": {
        "word": "direct marketing",
        "ipa": "/daɪˈrekt ˈmɑː.kɪ.tɪŋ/",
        "meaning": "tiếp thị trực tiếp",
        "example": "Direct marketing involves sending emails or flyers straight to customers."
    },
    "career 2": {
        "word": "occupation",
        "ipa": "/ˌɒk.jəˈpeɪ.ʃən/",
        "meaning": "nghề nghiệp, công việc chính",
        "example": "Please state your name, age, and occupation on the form."
    },
    "promotion 2": {
        "word": "advancement",
        "ipa": "/ədˈvɑːns.mənt/",
        "meaning": "sự tiến bộ, thăng tiến sự nghiệp",
        "example": "There are good opportunities for career advancement in this firm."
    },
    "freelancer 2": {
        "word": "contractor",
        "ipa": "/kənˈtræk.tər/",
        "meaning": "người làm việc theo hợp đồng, thầu phụ",
        "example": "The company hired an independent contractor to build the website."
    },
    "remote work 2": {
        "word": "telecommuting",
        "ipa": "/ˌtel.ɪ.kəˈmjuː.tɪŋ/",
        "meaning": "làm việc từ xa qua mạng máy tính",
        "example": "Telecommuting allows employees to work from home three days a week."
    },
    "networking 2": {
        "word": "socializing",
        "ipa": "/ˈsəʊ.ʃəl.aɪ.zɪŋ/",
        "meaning": "giao lưu xã hội, kết bạn",
        "example": "He spends his weekends socializing with his colleagues."
    },
    "skill set 2": {
        "word": "expertise",
        "ipa": "/ˌek.spɜːˈtiːz/",
        "meaning": "chuyên môn kỹ thuật, sự tinh thông",
        "example": "We need someone with expertise in software engineering."
    },
    "reference 2": {
        "word": "recommendation",
        "ipa": "/ˌrek.ə.menˈdeɪ.ʃən/",
        "meaning": "thư giới thiệu, sự tiến cử",
        "example": "A strong recommendation letter can help you get the job."
    },
    "workplace 2": {
        "word": "office",
        "ipa": "/ˈɒf.ɪs/",
        "meaning": "văn phòng làm việc",
        "example": "She works in a quiet office in downtown Hanoi."
    },
    "social media marketing 2": {
        "word": "online advertising",
        "ipa": "/ˈɒn.laɪn ˈæd.və.taɪ.zɪŋ/",
        "meaning": "quảng cáo trực tuyến",
        "example": "Online advertising is a highly effective way to reach target consumers."
    },
    "Destination 2": {
        "word": "Attraction",
        "ipa": "/əˈtrækʃn/",
        "meaning": "Điểm thu hút, điểm hấp dẫn khách du lịch",
        "example": "The Eiffel Tower is a major tourist attraction."
    },
    "Itinerary 2": {
        "word": "Schedule",
        "ipa": "/ˈʃedjuːl/",
        "meaning": "Lịch trình công việc, thời khóa biểu",
        "example": "We have a very busy schedule for the rest of the week."
    },
    "Accommodation 2": {
        "word": "Lodging",
        "ipa": "/ˈlɒdʒɪŋ/",
        "meaning": "Chỗ lưu trú, nơi trọ tạm thời",
        "example": "The cost of the tour includes food and lodging."
    },
    "Explore 2": {
        "word": "Discover",
        "ipa": "/dɪˈskʌvə(r)/",
        "meaning": "Phát hiện, khám phá ra điều mới",
        "example": "We discovered a beautiful hidden waterfall in the forest."
    },
    "Reservation 2": {
        "word": "Booking",
        "ipa": "/ˈbʊkɪŋ/",
        "meaning": "Sự đặt chỗ trước (phòng, vé)",
        "example": "I need to confirm our flight booking before Friday."
    },
    "Adventure 2": {
        "word": "Journey",
        "ipa": "/ˈdʒɜːni/",
        "meaning": "Hành trình dài, chuyến đi",
        "example": "They began their long journey across the continent."
    },
    "Excursion 2": {
        "word": "Outing",
        "ipa": "/ˈaʊtɪŋ/",
        "meaning": "Cuộc đi chơi, chuyến dã ngoại ngắn ngày",
        "example": "The school organized a summer outing to the seaside."
    },
    "Passenger 2": {
        "word": "Traveler",
        "ipa": "/ˈtrævlə(r)/",
        "meaning": "Người đi du lịch, khách lữ hành",
        "example": "The hostel welcomes budget travelers from all over the world."
    },
    "Automation 2": {
        "word": "Mechanization",
        "ipa": "/ˌmek.ə.naɪˈzeɪ.ʃən/",
        "meaning": "Cơ giới hóa bằng máy móc",
        "example": "The mechanization of farming increased food production."
    },
    "Database 2": {
        "word": "Repository",
        "ipa": "/rɪˈpɒz.ɪ.tər.i/",
        "meaning": "Kho lưu trữ dữ liệu, kho chứa",
        "example": "The university's online repository contains thousands of research papers."
    },
    "Software 2": {
        "word": "Application",
        "ipa": "/ˌæp.lɪˈkeɪ.ʃən/",
        "meaning": "Ứng dụng, chương trình phần mềm",
        "example": "You can install this mobile application on your tablet."
    },
    "Interface 2": {
        "word": "Dashboard",
        "ipa": "/ˈdæʃ.bɔːd/",
        "meaning": "Bảng điều khiển giao diện",
        "example": "The sales team monitors metrics on a real-time dashboard."
    },
    "Assistant 2": {
        "word": "Helper",
        "ipa": "/ˈhel.pər/",
        "meaning": "Người trợ giúp, người giúp đỡ",
        "example": "She works as a kitchen helper at a local restaurant."
    },
    "Analyze 2": {
        "word": "Examine",
        "ipa": "/ɪɡˈzæm.ɪn/",
        "meaning": "Xem xét kỹ lưỡng, khảo sát",
        "example": "The doctor will examine the patient to determine the cause."
    },
    "Prediction 2": {
        "word": "Forecast",
        "ipa": "/ˈfɔː.kɑːst/",
        "meaning": "Sự dự báo thời tiết hoặc kinh tế",
        "example": "The economic forecast suggests inflation will slow down."
    },
    "Algorithm 2": {
        "word": "Procedure",
        "ipa": "/prəˈsiː.dʒər/",
        "meaning": "Thủ tục, quy trình thực hiện",
        "example": "You must follow the standard safety procedure in the lab."
    },
    "Robot 2": {
        "word": "Machine",
        "ipa": "/məˈʃiːn/",
        "meaning": "Máy móc, thiết bị cơ khí",
        "example": "The printing machine produces hundreds of books per hour."
    },
    "Smart 2": {
        "word": "Clever",
        "ipa": "/ˈklev.ər/",
        "meaning": "Thông minh, khôn khéo, nhanh trí",
        "example": "She came up with a clever solution to the math problem."
    },
    "Data 2": {
        "word": "Facts",
        "ipa": "/fækts/",
        "meaning": "Sự thật, số liệu thực tế",
        "example": "The report is based on hard facts and figures."
    },
    "Code 2": {
        "word": "Script",
        "ipa": "/skrɪpt/",
        "meaning": "Kịch bản mã lệnh, đoạn mã script",
        "example": "I ran a simple python script to clean the data."
    },
    "App 2": {
        "word": "Tool",
        "ipa": "/tuːl/",
        "meaning": "Công cụ, dụng cụ làm việc",
        "example": "Computers are essential tools for modern education."
    },
    "User 2": {
        "word": "Client",
        "ipa": "/ˈklaɪ.ənt/",
        "meaning": "Khách hàng của công ty, máy khách",
        "example": "The lawyer met with her client to discuss the case."
    },
    "Web 2": {
        "word": "Net",
        "ipa": "/net/",
        "meaning": "Mạng lưới internet",
        "example": "She searched the net to find a cheap hotel room."
    },
    "Fast 2": {
        "word": "Quick",
        "ipa": "/kwɪk/",
        "meaning": "Nhanh chóng, mau lẹ",
        "example": "We had a quick lunch and returned to work."
    },
    "Computer 2": {
        "word": "Processor",
        "ipa": "/ˈprəʊ.ses.ər/",
        "meaning": "Bộ vi xử lý thông tin",
        "example": "The new chip is the fastest mobile processor in the world."
    },
    "System 2": {
        "word": "Structure",
        "ipa": "/ˈstrʌk.tʃər/",
        "meaning": "Cấu trúc, kết cấu hệ thống",
        "example": "The structural strength of the bridge was tested thoroughly."
    },
    "Network 2": {
        "word": "Connection",
        "ipa": "/kəˈnek.ʃən/",
        "meaning": "Sự kết nối, mối liên kết",
        "example": "There is a poor internet connection in this room."
    },
    "Program 2": {
        "word": "software",
        "word_alternative": "application", # Alternative if software conflicts
        "ipa": "/ˈsɒft.weər/",
        "meaning": "phần mềm máy tính",
        "example": "He installs free open-source software on his laptop."
    },
    "Digital 2": {
        "word": "Electronic",
        "ipa": "/ˌel.ekˈtrɒn.ɪk/",
        "meaning": "Thuộc về điện tử",
        "example": "Electronic commerce has grown rapidly over the years."
    },
    "Device 2": {
        "word": "Equipment",
        "ipa": "/ɪˈkwɪp.mənt/",
        "meaning": "Trang thiết bị máy móc",
        "example": "All laboratory equipment must be kept clean and organized."
    },
    "Storage 2": {
        "word": "Memory",
        "ipa": "/ˈmem.ər.i/",
        "meaning": "Bộ nhớ lưu trữ thông tin",
        "example": "The camera stores photos in its internal flash memory."
    },
    "Process 2": {
        "word": "Handle",
        "ipa": "/ˈhæn.dəl/",
        "meaning": "Xử lý, đối phó, giải quyết",
        "example": "She knows how to handle difficult customer queries."
    },
    "Neural network 2": {
        "word": "Deep network",
        "ipa": "/diːp ˈnet.wɜːk/",
        "meaning": "Mạng học sâu, mạng nơ-ron nhiều lớp",
        "example": "A deep network requires powerful hardware to train."
    },
    "Machine learning 2": {
        "word": "Pattern recognition",
        "ipa": "/ˈpæt.ən ˌrek.əɡˈnɪʃ.ən/",
        "meaning": "Sự nhận dạng khuôn mẫu",
        "example": "Pattern recognition is widely used in facial scan technology."
    },
    "Dataset 2": {
        "word": "Corpus",
        "ipa": "/ˈkɔː.pəs/",
        "meaning": "Tập hợp văn bản ngôn ngữ, kho ngữ liệu",
        "example": "The linguists analyzed a corpus of spoken English speeches."
    },
    "Optimization 2": {
        "word": "Tuning",
        "ipa": "/ˈtʃuː.nɪŋ/",
        "meaning": "Sự căn chỉnh, tinh chỉnh hiệu năng",
        "example": "Engine tuning can improve fuel efficiency and performance."
    },
    "Classification 2": {
        "word": "Categorization",
        "ipa": "/ˌkæt.ə.ɡər.aɪˈzeɪ.ʃən/",
        "meaning": "Sự chia nhóm, phân loại danh mục",
        "example": "The library uses a strict system for book categorization."
    },
    "Framework 2": {
        "word": "Library",
        "ipa": "/ˈlaɪ.brər.i/",
        "meaning": "Thư viện mã nguồn phần mềm",
        "example": "You can import this python library to handle HTTP requests."
    },
    "Generative 2": {
        "word": "Creative",
        "ipa": "/kriˈeɪ.tɪv/",
        "meaning": "Sáng tạo, mang tính sáng tạo",
        "example": "She has many creative ideas for the new marketing campaign."
    },
    "Autonomous 2": {
        "word": "Self-driving",
        "ipa": "/ˌselfˈdraɪ.vɪŋ/",
        "meaning": "Tự lái, tự điều khiển hành trình",
        "example": "Self-driving cars are expected to reduce traffic accidents."
    },
    "Cognitive computing 2": {
        "word": "Artificial brain",
        "ipa": "/ˌɑː.tɪˈfɪʃ.əl breɪn/",
        "meaning": "Não bộ nhân tạo",
        "example": "Scientists are trying to simulate an artificial brain using chips."
    },
    "Deep learning 2": {
        "word": "Representation learning",
        "ipa": "/ˌrep.rɪ.zenˈteɪ.ʃən ˈlɜː.nɪŋ/",
        "meaning": "Học biểu diễn tính năng",
        "example": "Representation learning discovers useful patterns in raw data."
    },
    "Reinforcement 2": {
        "word": "Feedback loops",
        "ipa": "/ˈfiːd.bæk luːps/",
        "meaning": "Vòng phản hồi điều khiển",
        "example": "Positive feedback loops can accelerate system growth."
    },
    "Transformers 2": {
        "word": "Attention mechanisms",
        "ipa": "/əˈten.ʃən ˈmek.ə.nɪz.əmz/",
        "meaning": "Cơ chế chú ý trong mạng nơ-ron",
        "example": "Attention mechanisms help neural networks focus on relevant words."
    },
    "Supervised 2": {
        "word": "Labeled learning",
        "ipa": "/ˈleɪ.bəld ˈlɜː.nɪŋ/",
        "meaning": "Học máy có gắn nhãn dữ liệu",
        "example": "Labeled learning is highly accurate but requires manual effort."
    },
    "Natural Language 2": {
        "word": "Human speech",
        "ipa": "/ˈhjuː.mən spiːtʃ/",
        "meaning": "Tiếng nói của con người",
        "example": "The computer system can transcribe human speech in real time."
    },
    "Hyperparameters 2": {
        "word": "Model settings",
        "ipa": "/ˈmɒd.əl ˈset.ɪŋz/",
        "meaning": "Thiết lập cấu hình mô hình",
        "example": "Adjusting model settings can significantly change the accuracy."
    },
    "Backpropagation 2": {
        "word": "Error propagation",
        "ipa": "/ˈer.ər ˌprɒp.əˈɡeɪ.ʃən/",
        "meaning": "Sự lan truyền sai số",
        "example": "Error propagation during calculations can lead to incorrect results."
    },
    "Ticket 2": {
        "word": "Pass",
        "ipa": "/pɑːs/",
        "meaning": "Vé thông hành, thẻ ra vào",
        "example": "You need a boarding pass to get onto the plane."
    },
    "Hotel 2": {
        "word": "Inn",
        "ipa": "/ɪn/",
        "meaning": "Nhà trọ nhỏ, khách sạn vùng quê",
        "example": "We stayed at a cozy country inn for the weekend."
    },
    "Bus 2": {
        "word": "Coach",
        "ipa": "/kəʊtʃ/",
        "meaning": "Xe khách liên tỉnh chất lượng cao",
        "example": "We traveled to Edinburgh by long-distance coach."
    },
    "Map 2": {
        "word": "Guide",
        "ipa": "/ɡaɪd/",
        "meaning": "Sách chỉ dẫn du lịch",
        "example": "The tourist guide contains helpful tips about local restaurants."
    },
    "Passport 2": {
        "word": "Visa",
        "ipa": "/ˈviː.zə/",
        "meaning": "Thị thực nhập cảnh",
        "example": "You need a tourist visa to enter the country."
    },
    "Fly 2": {
        "word": "Travel",
        "ipa": "/ˈtræv.əl/",
        "meaning": "Du hành, di chuyển du lịch",
        "example": "She loves to travel to exotic places during summer."
    },
    "Beach 2": {
        "word": "Coast",
        "ipa": "/kəʊst/",
        "meaning": "Bờ biển, vùng duyên hải",
        "example": "We walked along the beautiful rocky coast."
    },
    "Bag 2": {
        "word": "Luggage",
        "ipa": "/ˈlʌɡ.ɪdʒ/",
        "meaning": "Hành lý du lịch",
        "example": "You can leave your heavy luggage at the hotel reception."
    }
}

try:
    db = SessionLocal()
    # Lay danh sach tat ca tu hien tai dang co de loc xung dot
    all_vocabs = db.query(Vocabulary).all()
    all_words_lower = set(v.word.lower().strip() for v in all_vocabs)
    
    updated_count = 0
    
    # Duyet qua tat ca cac tu kết thúc bằng '2' hoac ' 2' trong db
    for v in all_vocabs:
        word_str = v.word.strip()
        if word_str.endswith('2') or word_str.endswith(' 2'):
            # Tim key trong replacements (lay word_str de map)
            rep_info = REPLACEMENTS.get(word_str)
            if not rep_info:
                # Neu khong co mapping san, thu bo chu so '2'
                if word_str.endswith(' 2'):
                    candidate = word_str[:-2].strip()
                else:
                    candidate = word_str[:-1].strip()
                
                # Neu candidate ko xung dot thi dung
                if candidate.lower() not in all_words_lower:
                    rep_info = {
                        "word": candidate,
                        "ipa": v.ipa,
                        "meaning": v.meaning,
                        "example": v.example
                    }
                else:
                    # Neu xung dot thi them hau to '_new' hoac tuong tu de dam bao khong trung
                    rep_info = {
                        "word": candidate + "_new",
                        "ipa": v.ipa,
                        "meaning": v.meaning,
                        "example": v.example
                    }
            
            # Kiem tra xem tu thay the co bi trung voi tu nao khac trong db ko
            target_word = rep_info["word"]
            if target_word.lower() in all_words_lower:
                # Neu bi trung, thu alternative neu co
                if "word_alternative" in rep_info:
                    target_word = rep_info["word_alternative"]
                
                # Neu van trung, sinh tu suffix de khong bao gio bi trung
                if target_word.lower() in all_words_lower:
                    i = 1
                    while f"{target_word}_{i}".lower() in all_words_lower:
                        i += 1
                    target_word = f"{target_word}_{i}"
            
            # Cap nhat vao DB
            old_name = v.word
            v.word = target_word
            if rep_info.get("ipa"):
                v.ipa = rep_info["ipa"]
            if rep_info.get("meaning"):
                v.meaning = rep_info["meaning"]
            if rep_info.get("example"):
                v.example = rep_info["example"]
                
            print(f"Cap nhat ID {v.id}: '{old_name}' -> '{v.word}'")
            updated_count += 1
            
            # Them tu moi vua cap nhat vao set de cac tu sau khong bi trung lap
            all_words_lower.add(v.word.lower().strip())
            
    db.commit()
    print(f"Hoan thanh cap nhat {updated_count} tu vung.")
    db.close()
except Exception as e:
    print("Error during update:", e)
