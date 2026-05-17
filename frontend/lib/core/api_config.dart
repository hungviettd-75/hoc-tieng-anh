class ApiConfig {
  static const String baseUrl = 'http://localhost:8000/api/v1';
  
  // Auth
  static const String login = '$baseUrl/auth/login';
  static const String register = '$baseUrl/auth/register';
  static const String me = '$baseUrl/auth/me';
  static const String refresh = '$baseUrl/auth/refresh';
  
  // Dashboard
  static const String dashboardStats = '$baseUrl/dashboard/stats';
  
  // Speaking
  static const String speaking = '$baseUrl/speaking';
  
  // Chat
  static const String chat = '$baseUrl/chat';
}
