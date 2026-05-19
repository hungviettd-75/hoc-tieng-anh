class ApiConfig {
  // 1. Hãy thay thế 'ai-english-coach-backend' bằng tên thực tế ứng dụng của bạn trên Render:
  static const String serverUrl = 'https://hoc-tieng-anh.onrender.com';
  
  // 2. Dưới đây là cấu hình kết nối nói chuyện Voice (WebSocket) - cũng thay tên tương tự:
  static const String wsUrl = 'wss://hoc-tieng-anh.onrender.com/api/v1';

  // Các phần bên dưới giữ nguyên tự động kết nối:
  static const String baseUrl = '$serverUrl/api/v1';
  static const String login = '$baseUrl/auth/login';
  static const String register = '$baseUrl/auth/register';
  static const String me = '$baseUrl/auth/me';
  static const String refresh = '$baseUrl/auth/refresh';
  static const String dashboardStats = '$baseUrl/dashboard/stats';
  static const String speaking = '$baseUrl/speaking';
  static const String chat = '$baseUrl/chat';
}
