FROM ubuntu:22.04 AS build-env

# Cài đặt các dependencies cần thiết cho Flutter
RUN apt-get update && apt-get install -y curl git wget unzip libgconf-2-4 gdb libstdc++6 libglu1-mesa fonts-droid-fallback lib32stdc++6 python3
RUN apt-get clean

# Clone Flutter repository
RUN git clone https://github.com/flutter/flutter.git /usr/local/flutter

# Thiết lập đường dẫn Flutter
ENV PATH="/usr/local/flutter/bin:/usr/local/flutter/bin/cache/dart-sdk/bin:${PATH}"

# Kích hoạt web support
RUN flutter channel stable
RUN flutter upgrade
RUN flutter config --enable-web

# Build frontend
WORKDIR /app
COPY . .
RUN flutter pub get
RUN flutter build web --release

# Sử dụng Nginx để serve static files
FROM nginx:alpine
COPY --from=build-env /app/build/web /usr/share/nginx/html

# Copy custom nginx config nếu có (tuỳ chọn)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
