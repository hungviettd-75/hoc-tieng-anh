import re

def test_regex(text):
    # Old regex
    clean = re.sub(r'[^\x00-\x7F\u00C0-\u1EF9\s,.?!:;\'"()]', '', text)
    return clean

texts = [
    "Tuyệt vời! Bạn phát âm chữ 'student' chưa đúng.",
    "Âm TH: đặt lưỡi nhẹ giữa hai răng rồi thổi hơi 😊",
    "Phải phát âm là: 'student' /ˈstjuːdnt/.",
    "Có 3 chỗ cần sửa. Thử lại từng cái nhé! 💪"
]

for t in texts:
    print(f"Original: {t}")
    print(f"Clean   : {test_regex(t)}")
    print("-" * 20)
