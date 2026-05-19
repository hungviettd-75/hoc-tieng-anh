import 'package:flutter/foundation.dart';

class ApiConfig {
  // 1. Hãy thay thế 'ai-english-coach-backend' bằng tên thực tế ứng dụng của bạn trên Render:
  static String get serverUrl {
    if (kDebugMode) {
      return 'http://127.0.0.1:8000';
    }
    return 'https://hoc-tieng-anh.onrender.com';
  }
  
  // 2. Dưới đây là cấu hình kết nối nói chuyện Voice (WebSocket) - cũng thay tên tương tự:
  static String get wsUrl {
    if (kDebugMode) {
      return 'ws://127.0.0.1:8000/api/v1';
    }
    return 'wss://hoc-tieng-anh.onrender.com/api/v1';
  }

  // Các phần bên dưới giữ nguyên tự động kết nối:
  static String get baseUrl => '$serverUrl/api/v1';
  static String get login => '$baseUrl/auth/login';
  static String get register => '$baseUrl/auth/register';
  static String get me => '$baseUrl/auth/me';
  static String get refresh => '$baseUrl/auth/refresh';
  static String get dashboardStats => '$baseUrl/dashboard/stats';
  static String get speaking => '$baseUrl/speaking';
  static String get chat => '$baseUrl/chat';
}
