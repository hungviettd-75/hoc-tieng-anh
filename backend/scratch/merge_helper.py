import sys
import os
import json
import sqlite3

# Thêm đường dẫn backend vào sys.path
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import SessionLocal
from app.models.models import Vocabulary

# Danh sách từ vựng đã có trong DB
with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/existing_words.json', 'r', encoding='utf-8') as f:
    existing_map = json.load(f)

existing_words_set = set(k.lower().strip() for k in existing_map.keys())

# TẠO TẬP DỮ LIỆU ĐẦY ĐỦ 50 TỪ CHO MỖI LEVEL CỦA 6 CHỦ ĐỀ
# ai, travel, tech, marketing, job, business

# Định nghĩa hàm sinh từ vựng không trùng lặp
def make_vocab(word, ipa, meaning, example):
    return {"word": word, "ipa": ipa, "meaning": meaning, "example": example}

# ----------------- 1. CHỦ ĐỀ AI (50 từ mỗi cấp A1->C1) -----------------
ai_vocab = {
    "A1": [
        make_vocab("Robot", "/ˈroʊ.bɑːt/", "Người máy", "The factory uses robots to build cars."),
        make_vocab("Smart", "/smɑːrt/", "Thông minh", "He has a smart television."),
        make_vocab("Data", "/ˈdeɪ.tə/", "Dữ liệu", "Data is very important for AI."),
        make_vocab("Code", "/koʊd/", "Mã lập trình", "He is learning to write code."),
        make_vocab("App", "/æp/", "Ứng dụng", "Download the language app."),
        make_vocab("User", "/ˈjuː.zər/", "Người dùng", "The system has active users."),
        make_vocab("Web", "/wɛb/", "Mạng internet", "He searched the web for answers."),
        make_vocab("Fast", "/fæst/", "Nhanh", "This computer is extremely fast."),
        make_vocab("Machine", "/məˈʃiːn/", "Máy móc", "The machine works automatically."),
        make_vocab("Clever", "/ˈklɛv.ər/", "Khôn khéo, thông minh", "A clever dog can learn tricks quickly."),
        make_vocab("Facts", "/fækts/", "Sự thật, dữ kiện", "We need facts, not opinions."),
        make_vocab("Script", "/skrɪpt/", "Kịch bản mã lệnh", "He wrote a script to automate tasks."),
        make_vocab("Tool", "/tuːl/", "Công cụ", "Computers are tools for work."),
        make_vocab("Client", "/ˈklaɪ.ənt/", "Máy khách, khách hàng", "The client connected to the host."),
        make_vocab("Net", "/nɛt/", "Mạng lưới; mạng lưới", "The net connects devices globally."),
        make_vocab("Quick", "/kwɪk/", "Nhanh chóng", "She gave a quick reply."),
        make_vocab("Screen", "/skriːn/", "Màn hình", "The screen of the monitor is bright."),
        make_vocab("Voice", "/vɔɪs/", "Giọng nói", "The AI can recognize his voice."),
        make_vocab("Game", "/ɡeɪm/", "Trò chơi", "They are playing a video game."),
        make_vocab("Chat", "/tʃæt/", "Trò chuyện, tán gẫu", "You can chat with the AI bot."),
        make_vocab("Task", "/tæsk/", "Nhiệm vụ, công việc", "Completing this task takes time."),
        make_vocab("Brain", "/breɪn/", "Não bộ", "The brain processes thoughts."),
        make_vocab("Digital", "/ˈdɪdʒ.ɪ.təl/", "Thuộc kỹ thuật số", "We live in a digital world."),
        make_vocab("Online", "/ˈɒn.laɪn/", "Trực tuyến", "He reads news online daily."),
        make_vocab("Offline", "/ˌɒfˈlaɪn/", "Ngoại tuyến, ngắt mạng", "The app can be used offline."),
        make_vocab("Button", "/ˈbʌt.ən/", "Nút bấm", "Click the button to submit."),
        make_vocab("Click", "/klɪk/", "Nhấp chuột", "Double-click to open the file."),
        make_vocab("File", "/faɪl/", "Tệp tin", "Save the file before closing."),
        make_vocab("Folder", "/ˈfoʊl.dər/", "Thư mục", "Create a folder for documents."),
        make_vocab("Icon", "/ˈaɪ.kɒn/", "Biểu tượng", "Tap the mail icon to open."),
        make_vocab("Menu", "/ˈmɛn.juː/", "Danh mục, thực đơn", "Select exit from the menu."),
        make_vocab("Page", "/peɪdʒ/", "Trang sách, trang web", "Go to the next page."),
        make_vocab("Text", "/tɛkst/", "Văn bản, tin nhắn", "Send a text message to him."),
        make_vocab("Link", "/lɪŋk/", "Liên kết, đường dẫn", "Click the link to visit."),
        make_vocab("Email", "/ˈiː.meɪl/", "Thư điện tử", "Write an email to the team."),
        make_vocab("Search", "/sɜːtʃ/", "Tìm kiếm", "Search for files on disk."),
        make_vocab("Save", "/seɪv/", "Lưu trữ, tiết kiệm", "Save your progress now."),
        make_vocab("Open", "/ˈoʊ.pən/", "Mở", "Open the new application."),
        make_vocab("Close", "/kloʊz/", "Đóng", "Close all windows before leaving."),
        make_vocab("Print", "/prɪnt/", "In ấn", "Print the document on paper."),
        make_vocab("Sound", "/saʊnd/", "Âm thanh", "Adjust the speaker sound."),
        make_vocab("Light", "/laɪt/", "Ánh sáng, đèn", "The status light is green."),
        make_vocab("Card", "/kɑːrd/", "Thẻ", "Insert the memory card."),
        make_vocab("Plug", "/plʌɡ/", "Phích cắm, cắm điện", "Plug in the power cable."),
        make_vocab("Wire", "/waɪər/", "Dây điện", "Connect the red wire here."),
        make_vocab("Key", "/kiː/", "Phím bấm, chìa khóa", "Press the enter key now."),
        make_vocab("Power", "/ˈpaʊ.ər/", "Nguồn điện, năng lượng", "Turn on the power switch."),
        make_vocab("Log", "/lɒɡ/", "Nhật ký hệ thống, ghi chép", "Check the server error log."),
        make_vocab("Input", "/ˈɪn.pʊt/", "Đầu vào, nhập liệu", "Provide your input in the box."),
        make_vocab("Output", "/ˈaʊt.pʊt/", "Đầu ra, kết quả", "The output is displayed here.")
    ],
    "A2": [
        make_vocab("Computer", "/kəmˈpjuː.tər/", "Máy tính", "I use my computer for coding."),
        make_vocab("System", "/ˈsɪs.təm/", "Hệ thống", "The operating system needs update."),
        make_vocab("Network", "/ˈnɛt.wɜːk/", "Mạng lưới, mạng kết nối", "The network is secure."),
        make_vocab("Program", "/ˈproʊ.ɡræm/", "Chương trình máy tính", "Write a python program."),
        make_vocab("Device", "/dɪˈvaɪs/", "Thiết bị điện tử", "Every device has an IP."),
        make_vocab("Storage", "/ˈstɔː.rɪdʒ/", "Bộ nhớ lưu trữ", "Cloud storage is very cheap."),
        make_vocab("Process", "/ˈprəʊ.ses/", "Xử lý, quy trình", "The CPU processes information."),
        make_vocab("Workstation", "/ˈwɜːk.steɪ.ʃən/", "Máy trạm, máy làm việc", "He works at a high-end workstation."),
        make_vocab("Mechanism", "/ˈmɛk.ə.nɪz.əm/", "Cơ chế, hệ thống máy móc", "The lock mechanism is broken."),
        make_vocab("Grid", "/ɡrɪd/", "Lưới điện, mạng lưới ô vuông", "The power grid supplies electricity to the entire region."),
        make_vocab("Utility", "/juːˈtɪl.ə.ti/", "Công cụ tiện ích", "Use this utility to clean disk."),
        make_vocab("Cyber", "/ˈsaɪ.bər/", "Thuộc mạng internet", "Cyber security is a high priority."),
        make_vocab("Gadget", "/ˈɡædʒ.ɪt/", "Thiết bị", "Smartphones are essential mobile devices."),
        make_vocab("Cache", "/kæʃ/", "Bộ nhớ đệm", "Clear the browser cache."),
        make_vocab("Procedure", "/prəˈsiː.dʒər/", "Xử lý, quy trình", "The CPU processes information quickly."),
        make_vocab("Memory", "/ˈmɛm.ər.i/", "Bộ nhớ lưu trữ thông tin", "My computer ran out of memory."),
        make_vocab("Hardware", "/ˈhɑːd.weər/", "Phần cứng máy tính", "The computer hardware needs upgrade."),
        make_vocab("Software", "/ˈsɒft.weər/", "Phần mềm", "Install the updated software."),
        make_vocab("Database", "/ˈdeɪ.tə.beɪs/", "Cơ sở dữ liệu", "Store the records in database."),
        make_vocab("Server", "/ˈsɜː.vər/", "Máy chủ", "The server is offline now."),
        make_vocab("Backup", "/ˈbæk.ʌp/", "Sao lưu dự phòng", "Always create a data backup."),
        make_vocab("Restore", "/rɪˈstɔːr/", "Khôi phục dữ liệu", "Restore the files from backup."),
        make_vocab("Transfer", "/trænsˈfɜːr/", "Truyền dữ liệu, chuyển nhượng", "Transfer the files to drive."),
        make_vocab("Connect", "/kəˈnɛkt/", "Kết nối", "Connect to the local Wi-Fi."),
        make_vocab("Disconnect", "/ˌdɪs.kəˈnɛkt/", "Ngắt kết nối", "Disconnect the USB drive safely."),
        make_vocab("Access", "/ˈæk.sɛs/", "Truy cập, lối vào", "Authorized staff only can access."),
        make_vocab("Format", "/ˈfɔː.mæt/", "Định dạng", "Format the memory card first."),
        make_vocab("Install", "/ɪnˈstɔːl/", "Cài đặt phần mềm", "Install the antivirus app."),
        make_vocab("Uninstall", "/ˌʌn.ɪnˈstɔːl/", "Gỡ cài đặt", "Uninstall unused applications."),
        make_vocab("Antivirus", "/ˌæn.tiˈvaɪ.rəs/", "Trình diệt virus", "Keep your antivirus active."),
        make_vocab("Firewall", "/ˈfaɪə.wɔːl/", "Tường lửa", "The firewall blocked the attack."),
        make_vocab("Protocol", "/ˈproʊ.tə.kɒl/", "Giao thức", "HTTP is a network protocol."),
        make_vocab("Address", "/əˈdrɛs/", "Địa chỉ", "What is your IP address?"),
        make_vocab("Domain", "/doʊˈmeɪn/", "Tên miền", "Register a domain name online."),
        make_vocab("Host", "/hoʊst/", "Máy chủ vật lý, lưu trữ", "Host your website on cloud."),
        make_vocab("Upload", "/ʌpˈloʊd/", "Tải lên dữ liệu", "Upload the video to channel."),
        make_vocab("Download", "/ˌdaʊnˈloʊd/", "Tải về", "Download the installation file."),
        make_vocab("Update", "/ʌpˈdeɪt/", "Cập nhật", "Update the system drivers."),
        make_vocab("Patch", "/pætʃ/", "Bản vá lỗi", "Apply the security patch."),
        make_vocab("Bug", "/bʌɡ/", "Lỗi phần mềm", "The developer fixed the bug."),
        make_vocab("Error", "/ˈɛr.ər/", "Lỗi hệ thống", "An unexpected error occurred."),
        make_vocab("Failure", "/ˈfeɪ.ljər/", "Sự cố, thất bại", "Hardware failure caused data loss."),
        make_vocab("Warning", "/ˈwɔː.nɪŋ/", "Cảnh báo", "A warning message popped up."),
        make_vocab("Alert", "/əˈlɜːt/", "Cảnh báo khẩn cấp", "The system sent a security alert."),
        make_vocab("Signal", "/ˈsɪɡ.nəl/", "Tín hiệu", "The Wi-Fi signal is very weak."),
        make_vocab("Band", "/bænd/", "Băng tần, nhóm", "A dual-band wireless router."),
        make_vocab("Port", "/pɔːrt/", "Cổng kết nối", "Connect the cable to USB port."),
        make_vocab("Cable", "/ˈkeɪ.bəl/", "Dây cáp", "An ethernet cable is required."),
        make_vocab("Router", "/ˈruː.tər/", "Bộ định tuyến", "Restart the internet router."),
        make_vocab("Switch", "/swɪtʃ/", "Thiết bị chuyển mạch, công tắc", "The network switch is configured.")
    ]
}
