import 'package:flutter/foundation.dart';

class ApiConfig {
  // 1. Hãy thay thế 'ai-english-coach-backend' bằng tên thực tế ứng dụng của bạn trên Render:
  static String get serverUrl {
    if (kIsWeb) {
      final uri = Uri.base;
      if (uri.host == 'localhost' || uri.host == '127.0.0.1' || uri.host.startsWith('192.168.')) {
        return 'http://${uri.host}:8000';
      }
    }
    if (kDebugMode) {
      return 'http://127.0.0.1:8000';
    }
    return 'https://ai-english-coach-backend.onrender.com';
  }
  
  static String get wsUrl {
    if (kIsWeb) {
      final uri = Uri.base;
      if (uri.host == 'localhost' || uri.host == '127.0.0.1' || uri.host.startsWith('192.168.')) {
        return 'ws://${uri.host}:8000/api/v1';
      }
    }
    if (kDebugMode) {
      return 'ws://127.0.0.1:8000/api/v1';
    }
    return 'wss://ai-english-coach-backend.onrender.com/api/v1';
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
// Trigger deploy

