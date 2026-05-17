# 📝 TÓM TẮT NGỮ CẢNH: TRIỂN KHAI CHUYÊN NGHIỆP (PHASE 1)

**Ngày ghi nhận:** 16/05/2026
**Trạng thái:** Đang thực hiện Giai đoạn 1 (Chuẩn bị và đưa code lên GitHub).

---

## 🛠️ 1. Các công việc đã hoàn thành
- [x] **Tạo file `backend/Procfile`**: Đã cấu hình lệnh khởi chạy server cho Render (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
- [x] **Kiểm tra `backend/requirements.txt`**: Xác nhận đầy đủ các thư viện cần thiết (FastAPI, Gemini, SQLAlchemy...).
- [x] **Thiết lập `.gitignore`**: Đã tạo file tại thư mục gốc để loại bỏ các file rác, file build và thông tin bảo mật khỏi GitHub.
- [x] **Kiểm tra Git cục bộ**: Xác nhận máy học viên đã cài đặt Git nhưng chưa khởi tạo repository cho dự án này.

---

## 🚀 2. Các bước cần thực hiện tiếp theo (Next Steps)
1. **Đưa code lên GitHub:**
   - Chạy các lệnh `git init`, `git add`, `git commit`.
   - Tạo Repository trên GitHub và chạy lệnh `git push` để đẩy code lên.
2. **Triển khai Backend trên Render.com:**
   - Kết nối GitHub với Render.
   - Thiết lập các biến môi trường (Environment Variables): `GEMINI_API_KEY`, `DATABASE_URL`.
   - Lấy đường dẫn API chính thức (ví dụ: `https://api-hoc-tieng-anh.onrender.com`).
3. **Cấu hình lại Frontend:**
   - Cập nhật địa chỉ API mới vào file `frontend/lib/core/api_config.dart`.
4. **Triển khai Frontend trên Vercel:**
   - Chạy lệnh `flutter build web --release`.
   - Đẩy thư mục `build/web` lên Vercel để lấy link sử dụng trên điện thoại.

---

## 💡 Ghi chú quan trọng
- Cần nhắc học viên bảo mật file `.env` và API Key, chỉ nhập chúng trực tiếp trên giao diện quản lý của Render/Vercel.
- Khi chạy trên điện thoại qua internet, mọi tính năng Realtime Voice sẽ cần HTTPS (Render và Vercel đã hỗ trợ sẵn cái này).

**Hệ thống đã sẵn sàng cho bước đẩy code lên Cloud!**
