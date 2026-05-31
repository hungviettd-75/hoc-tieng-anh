import sqlite3
import re

# Danh sách các từ có nghĩa sai cần sửa lại cho đúng
# Định dạng: word -> (meaning_đúng, ipa_đúng, example_đúng)
CORRECTIONS = {
    # Các từ thay thế nhưng còn mang nghĩa của từ gốc
    "Net": ("Lưới; mạng lưới", "/nɛt/", "The fisherman cast his net into the sea."),
    "net": ("Lưới; mạng lưới", "/nɛt/", "The fisherman cast his net into the sea."),
    "clip": ("Đoạn video ngắn; kẹp giấy", "/klɪp/", "She shared a funny clip on social media."),
    "Clip": ("Đoạn video ngắn; kẹp giấy", "/klɪp/", "She shared a funny clip on social media."),
    "lens": ("Ống kính máy ảnh; thấu kính", "/lɛnz/", "She bought a new wide-angle lens for her camera."),
    "Lens": ("Ống kính máy ảnh; thấu kính", "/lɛnz/", "She bought a new wide-angle lens for her camera."),
    "match": ("Trận đấu; diêm quẹt", "/mæʧ/", "The match between the two teams was exciting."),
    "Match": ("Trận đấu; diêm quẹt", "/mæʧ/", "The match between the two teams was exciting."),
    "mobile": ("Điện thoại di động", "/ˈmoʊbəl/", "She checked her messages on her mobile."),
    "Mobile": ("Điện thoại di động", "/ˈmoʊbəl/", "She checked her messages on her mobile."),
    "fetch": ("Lấy về, tải về", "/fɛʧ/", "The browser will fetch the data from the server."),
    "Fetch": ("Lấy về, tải về", "/fɛʧ/", "The browser will fetch the data from the server."),
    "site": ("Địa điểm; trang web", "/saɪt/", "We visited the historic site in the city center."),
    "Site": ("Địa điểm; trang web", "/saɪt/", "We visited the historic site in the city center."),
    "passcode": ("Mã PIN, mật khẩu số", "/ˈpæsˌkoʊd/", "Enter your passcode to unlock the phone."),
    "Passcode": ("Mã PIN, mật khẩu số", "/ˈpæsˌkoʊd/", "Enter your passcode to unlock the phone."),
    "upgrade": ("Nâng cấp lên phiên bản mới hơn", "/ˈʌpˌɡreɪd/", "It's time to upgrade your computer's operating system."),
    "Upgrade": ("Nâng cấp lên phiên bản mới hơn", "/ˈʌpˌɡreɪd/", "It's time to upgrade your computer's operating system."),
    "link": ("Liên kết, đường dẫn", "/lɪŋk/", "Click the link to visit the website."),
    "Link": ("Liên kết, đường dẫn", "/lɪŋk/", "Click the link to visit the website."),
    "text": ("Tin nhắn văn bản; văn bản", "/tɛkst/", "She sent a text to her friend after the meeting."),
    "Text": ("Tin nhắn văn bản; văn bản", "/tɛkst/", "She sent a text to her friend after the meeting."),
    "power cell": ("Pin, nguồn điện dự phòng", "/ˈpaʊər sɛl/", "This device uses a rechargeable power cell."),
    "Power cell": ("Pin, nguồn điện dự phòng", "/ˈpaʊər sɛl/", "This device uses a rechargeable power cell."),
    "electronic mail": ("Thư điện tử", "/ɪˌlɛkˈtrɒnɪk meɪl/", "Send me the report by electronic mail."),
    "Electronic mail": ("Thư điện tử", "/ɪˌlɛkˈtrɒnɪk meɪl/", "Send me the report by electronic mail."),
    
    # Các từ thay thế nhóm AI còn mang nghĩa của từ gốc
    "Grid": ("Lưới điện, mạng lưới ô vuông", "/ɡrɪd/", "The power grid supplies electricity to the entire region."),
    "Aide": ("Trợ lý, người giúp đỡ", "/eɪd/", "The president's aide arranged the meeting schedule."),
    "Console": ("Bảng điều khiển; máy chơi game", "/ˈkɒnsoʊl/", "The game console was connected to the television."),
    "Corpus": ("Kho ngữ liệu văn bản", "/ˈkɔːpəs/", "Linguists use a corpus to study language patterns."),
    "Mechanization": ("Cơ giới hóa sản xuất", "/ˌmɛkənəˈzeɪʃən/", "Mechanization replaced many manual labor jobs in factories."),
    "Fine-tuning": ("Tinh chỉnh mô hình AI", "/faɪn ˈtjuːnɪŋ/", "Fine-tuning a pre-trained model improves its performance on specific tasks."),
    "Infrastructure": ("Cơ sở hạ tầng kỹ thuật", "/ˈɪnfrəˌstrʌktʃər/", "The company invested in new IT infrastructure to support growth."),
    "Feedback loop": ("Vòng phản hồi học tăng cường", "/ˈfiːdbæk luːp/", "A feedback loop helps the AI model improve over time."),
    "Gradient descent": ("Phương pháp hạ gradient (tối ưu hóa)", "/ˈɡreɪdiənt dɪˈsɛnt/", "Gradient descent is used to minimize the loss function in training."),
    "Guided learning": ("Học có giám sát, học theo hướng dẫn", "/ˈɡaɪdɪd ˈlɜːnɪŋ/", "Guided learning uses labeled data to train the AI model."),
    "Speech recognition": ("Nhận dạng giọng nói", "/spiːʧ ˌrɛkəɡˈnɪʃən/", "Speech recognition technology converts spoken words into text."),
    "Model parameters": ("Tham số mô hình AI", "/ˈmɒdəl pəˈræmɪtəz/", "Tuning model parameters is essential for better accuracy."),
    "Attention mechanism": ("Cơ chế chú ý trong AI", "/əˈtenʃən ˈmɛkənɪzəm/", "The attention mechanism allows the model to focus on relevant parts of the input."),
    "Artificial brain": ("Não bộ nhân tạo, trí tuệ nhân tạo", "/ɑːˈtɪfɪʃəl breɪn/", "Researchers are developing an artificial brain to simulate human cognition."),
    "Deep network": ("Mạng nơ-ron sâu nhiều lớp", "/diːp ˈnɛtwɜːk/", "A deep network can learn complex patterns from large datasets."),
    "Neural computing": ("Điện toán nơ-ron", "/ˈnjʊərəl kəmˈpjuːtɪŋ/", "Neural computing mimics the way the human brain processes information."),
    
    # Nhóm du lịch
    "Discover": ("Phát hiện ra, tìm thấy điều mới", "/dɪˈskʌvər/", "Explorers discovered new lands in the 15th century."),
    "Journey": ("Hành trình dài, chuyến đi", "/ˈdʒɜːni/", "The journey from Hanoi to Ho Chi Minh City takes about two hours by plane."),
    "Outing": ("Chuyến dã ngoại, đi chơi ngoài", "/ˈaʊtɪŋ/", "The whole family went on an outing to the countryside."),
    "Traveler": ("Người đi du lịch, lữ khách", "/ˈtræv.əl.ər/", "The traveler packed light for the long trip."),
    "Inn": ("Quán trọ, nhà nghỉ nhỏ", "/ɪn/", "We spent the night at a cozy inn near the forest."),
    "Visa": ("Thị thực nhập cảnh", "/ˈviːzə/", "You need a valid visa to enter the United States."),
    "Booking": ("Đặt chỗ, đặt phòng trước", "/ˈbʊkɪŋ/", "Please confirm your booking at least 24 hours in advance."),
    "Lodging": ("Chỗ trọ, nơi ở tạm", "/ˈlɒdʒɪŋ/", "The hotel provides comfortable lodging for tourists."),
    "Attraction": ("Điểm tham quan, địa điểm hấp dẫn", "/əˈtrækʃən/", "The Eiffel Tower is Paris's most famous tourist attraction."),
    
    # Nhóm kinh doanh / công việc
    "target": ("Mục tiêu cần đạt được", "/ˈtɑːɡɪt/", "The sales team hit their monthly target."),
    "transaction": ("Giao dịch tài chính", "/trænˈzækʃən/", "The bank recorded every transaction in its system."),
    "enterprise": ("Doanh nghiệp lớn", "/ˈɛntəpraɪz/", "She founded a successful enterprise in the tech sector."),
    "commerce": ("Thương mại, hoạt động mua bán", "/ˈkɒmɜːs/", "E-commerce has grown rapidly in recent years."),
    "depository": ("Kho lưu trữ, ngân hàng lưu ký", "/dɪˈpɒzɪtri/", "The securities depository holds shares on behalf of investors."),
    "blueprint": ("Bản vẽ kỹ thuật; kế hoạch chi tiết", "/ˈbluːˌprɪnt/", "The architect showed us the blueprint for the new building."),
    
    # Nhóm marketing
    "trendsetter": ("Người dẫn đầu xu hướng", "/ˈtrɛndˌsɛtər/", "She is a trendsetter in the fashion industry."),
    "CLV": ("Giá trị trọn đời khách hàng", "/ˌsiːɛlˈviː/", "Increasing CLV is key to sustainable business growth."),
    
    # Nhóm thay thế giữ nguyên nghĩa sai của từ gốc (IT security, VR, ...)
    "IT security": ("Bảo mật hệ thống công nghệ thông tin", "/ˌaɪˈtiː sɪˈkjʊərɪti/", "IT security teams protect company data from cyberattacks."),
    "capacity": ("Dung lượng; năng lực", "/kəˈpæsɪti/", "The hard drive has a storage capacity of 1 terabyte."),
    "smart tech": ("Công nghệ thông minh", "/smɑːrt tɛk/", "Wearable smart tech can monitor your heart rate and steps."),
    "broadcasting": ("Phát sóng, truyền hình/phát thanh", "/ˈbrɔːdkɑːstɪŋ/", "The live broadcasting of the match attracted millions of viewers."),
    "device": ("Thiết bị điện tử", "/dɪˈvaɪs/", "Every device in the smart home is connected to the internet."),
    "telephone": ("Điện thoại (cố định)", "/ˈtɛlɪfoʊn/", "He called me on the telephone to confirm the meeting."),
    "display": ("Màn hình hiển thị", "/dɪˈspleɪ/", "The new phone has a sharp, high-resolution display."),
    
    # IT security IPA cũng cần sửa
}

conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

fixed_db = 0
for word, (meaning, ipa_val, example) in CORRECTIONS.items():
    c.execute("""
        UPDATE vocabularies SET meaning=?, ipa=?, example=?
        WHERE word=? COLLATE NOCASE
    """, (meaning, ipa_val, example, word))
    if c.rowcount > 0:
        fixed_db += c.rowcount
        print(f"DB Fixed: {word} -> {meaning}")

conn.commit()
conn.close()
print(f"\nTotal DB rows fixed: {fixed_db}")

# Cập nhật trong learn.py
FILE_PATH = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py'
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

fixed_file = 0
for word, (meaning, ipa_val, example) in CORRECTIONS.items():
    pattern = rf'("word":\s*"{re.escape(word)}",\s*"ipa":\s*")[^"]+(",\s*"meaning":\s*")[^"]+(",\s*"example":\s*")[^"]+(")'
    replacement = rf'\1{ipa_val}\2{meaning}\3{example}\4'
    new_content, count = re.subn(pattern, replacement, content, flags=re.IGNORECASE)
    if count > 0:
        content = new_content
        fixed_file += count
        print(f"File Fixed: {word} ({count}x)")

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nTotal file entries fixed: {fixed_file}")

# Verify syntax
import py_compile
try:
    py_compile.compile(FILE_PATH, doraise=True)
    print("learn.py syntax OK")
except py_compile.PyCompileError as e:
    print("Syntax ERROR:", e)
