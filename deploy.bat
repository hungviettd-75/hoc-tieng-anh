@echo off
chcp 65001 > nul
title Bộ công cụ Tự động hóa Deploy - AI English Coach

echo =======================================================================
echo              BỘ CÔNG CỤ TỰ ĐỘNG HÓA DEPLOY - AI ENGLISH COACH           
echo =======================================================================
echo.
echo Script này sẽ giúp bạn tự động kiểm tra code, commit và đẩy lên GitHub.
echo Hệ thống CI/CD (GitHub Actions và Vercel) sẽ tự động kích hoạt và cập nhật
echo ứng dụng lên internet ngay lập tức.
echo.
echo [1] Đang kiểm tra trạng thái Git cục bộ...
git status
echo.

set /p msg="👉 Nhập nội dung cập nhật (Commit Message) của bạn: "
if "%msg%"=="" (
    set msg="update: tự động cập nhật hệ thống"
)

echo.
echo [2] Đang chuẩn bị tệp tin để commit...
git add .

echo.
echo [3] Đang tạo commit với thông điệp: %msg%
git commit -m %msg%

echo.
echo [4] Đang đẩy mã nguồn lên GitHub (Kích hoạt tự động deploy lên internet)...
git push origin main

if %errorlevel% neq 0 (
    echo.
    echo ❌ Đã xảy ra lỗi trong quá trình đẩy mã nguồn lên GitHub.
    echo Vui lòng kiểm tra lại kết nối internet hoặc quyền truy cập repository.
    goto end
)

echo.
echo =======================================================================
echo 🎉 ĐÃ ĐẨY MÃ NGUỒN LÊN GITHUB THÀNH CÔNG!
echo =======================================================================
echo.
echo Hệ thống internet đang tự động xử lý:
echo 1. Frontend: Đang được GitHub Actions build và deploy lên Vercel.
echo    (Thời gian xử lý dự kiến: 2-3 phút. Bạn sẽ thấy giao diện mới ngay lập tức)
echo 2. Backend: Đang được Render tự động kéo code mới nhất và cập nhật.
echo.
echo 💡 MẸO: Trình duyệt của bạn sẽ tự động nhận diện bản mới mà không bị kẹt cache cũ.
echo.

:end
pause
