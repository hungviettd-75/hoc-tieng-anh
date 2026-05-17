# Hướng dẫn Triển khai & Sử dụng AI English Coach

Tài liệu này hướng dẫn chi tiết cách chạy dự án ở môi trường Local (máy tính cá nhân) và cách triển khai lên Production (Google Cloud Platform).

---

## Phần 1: Chạy dự án ở Local bằng Docker Compose (Khuyên dùng để test)

Đây là cách nhanh nhất để khởi chạy toàn bộ hệ thống (Frontend, Backend, Database, Redis, Monitoring) mà không cần cài đặt lẻ tẻ từng công cụ.

### 1. Yêu cầu hệ thống
- Đã cài đặt **Docker** và **Docker Compose** (Khuyến nghị dùng Docker Desktop trên Windows/Mac).
- Mở Terminal/PowerShell tại thư mục gốc của dự án (`e:\Project\Hoc\hoc-tieng-anh`).

### 2. Các bước khởi chạy
**Bước 1:** Kiểm tra/Cập nhật file `.env` ở thư mục gốc (nếu có) để đảm bảo bạn đã cung cấp đủ API keys (GEMINI_API_KEY, PINECONE_API_KEY, v.v.).

**Bước 2:** Build và khởi chạy tất cả các services:
```bash
docker-compose -f docker-compose.prod.yml up --build -d
```
*(Tham số `-d` giúp chạy ngầm dưới background. Lần đầu build sẽ mất thời gian khá lâu do phải build Flutter Web và tải các Docker image).*

**Bước 3:** Kiểm tra trạng thái:
```bash
docker-compose -f docker-compose.prod.yml ps
```

**Bước 4:** Truy cập các ứng dụng:
- **Frontend App**: `http://localhost:80` (Mở trên trình duyệt)
- **Backend API Docs**: `http://localhost:8000/docs`
- **Admin Dashboard**: `http://localhost:8000/admin`
- **Grafana (Monitoring)**: `http://localhost:3000` (User/Pass mặc định: `admin` / `admin`)
- **Prometheus**: `http://localhost:9090`

**Bước 5:** Dừng hệ thống khi không dùng:
```bash
docker-compose -f docker-compose.prod.yml down
```

---

## Phần 2: Triển khai lên Production (Google Cloud Platform - GKE)

Dự án đã được thiết lập sẵn **GitHub Actions CI/CD** và **Kubernetes Manifests** để tự động hoá deploy lên cụm GKE (Google Kubernetes Engine).

### 1. Chuẩn bị trên Google Cloud
1. Tạo một Project trên GCP.
2. Bật API cho **Kubernetes Engine (GKE)** và **Container Registry (GCR)**.
3. Tạo một GKE Cluster có tên `ai-coach-cluster` ở zone `us-central1-a` (bạn có thể đổi tên này trong file `.github/workflows/production.yml`).
4. Tạo một Service Account có quyền (roles) sau:
   - Kubernetes Engine Developer
   - Storage Admin (để push ảnh lên GCR)
5. Tạo JSON key cho Service Account này.

### 2. Thiết lập GitHub Secrets
Vào kho lưu trữ mã nguồn của bạn trên GitHub -> **Settings** -> **Secrets and variables** -> **Actions** -> Thêm các biến sau:
- `GCP_PROJECT_ID`: ID của project trên GCP.
- `GCP_CREDENTIALS`: Nội dung file JSON key bạn vừa tạo ở trên.

### 3. Quy trình Deploy Tự động
Mỗi khi bạn `git commit` và `git push` code lên nhánh `main`:
1. GitHub Actions sẽ tự động kích hoạt.
2. Nó sẽ tự động Build Backend & Frontend thành Docker image.
3. Đẩy (Push) image lên Google Container Registry.
4. Cập nhật thẻ (tag) của image vào các file Kubernetes YAML.
5. Apply toàn bộ manifests vào cụm GKE của bạn.

### 4. Cấu hình bảo mật Kubernetes (Quan trọng)
Trước khi pipeline chạy thành công, bạn cần tạo **Secrets** thực tế trong GKE để lưu thông tin nhạy cảm.
Mở Cloud Shell trên GCP và chạy các lệnh thay thế các giá trị bên dưới:
```bash
kubectl create namespace ai-coach-prod

kubectl create secret generic ai-coach-secrets \
  --namespace=ai-coach-prod \
  --from-literal=POSTGRES_USER=admin \
  --from-literal=POSTGRES_PASSWORD=MatKhauKhoDoan123! \
  --from-literal=SECRET_KEY=khoa_bi_mat_cua_jwt_token \
  --from-literal=GEMINI_API_KEY=api_key_gemini_cua_ban
```

---

## Phần 3: Cách thức hoạt động của các thành phần mở rộng

1. **Celery Worker & Redis**:
   - Thay vì Backend tự xử lý các tác vụ AI mất thời gian, nó sẽ gửi tin nhắn vào Redis.
   - Các container `celery_worker` sẽ đọc tin nhắn từ Redis và xử lý ngầm (background task). Nếu lượng task quá lớn, Kubernetes HPA sẽ tự động nhân bản (scale-up) thêm nhiều worker.
2. **Rate Limiting (SlowAPI)**:
   - Backend đã tích hợp chống DDoS. Nếu một user gọi API quá nhiều lần trong 1 phút, họ sẽ bị từ chối (`429 Too Many Requests`).
3. **Monitoring**:
   - Prometheus tự động lấy dữ liệu (metric) CPU/RAM/Request từ Backend. Grafana kết nối vào Prometheus để hiển thị thành các biểu đồ trực quan.
