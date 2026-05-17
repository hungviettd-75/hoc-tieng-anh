import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ai_english_coach/features/auth/models/user_model.dart';
import 'package:ai_english_coach/core/api_config.dart';


class AuthService {
  // BƯỚC QUAN TRỌNG: Thay 'localhost' bằng IP thực tế nếu chạy trên Mobile
  // Sử dụng ApiConfig.baseUrl


  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      print('DEBUG: Attempting login for $email at ${ApiConfig.login}');
      final response = await http.post(
        Uri.parse(ApiConfig.login),
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: {
          'username': email,
          'password': password,
        },
      ).timeout(const Duration(seconds: 10));

      print('DEBUG: Login response status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        await _saveTokens(data['access_token'], data['refresh_token']);
        return data;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Login failed');
      }
    } catch (e) {
      print('DEBUG: Login error: $e');
      rethrow;
    }
  }

  Future<UserModel> getCurrentUser() async {
    try {
      print('DEBUG: Getting current user from ${ApiConfig.me}');
      final headers = await getAuthHeaders();
      final response = await http.get(
        Uri.parse(ApiConfig.me),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      print('DEBUG: GetUser response status: ${response.statusCode}');

      if (response.statusCode == 200) {
        return UserModel.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Failed to get user profile');
      }
    } catch (e) {
      print('DEBUG: GetUser error: $e');
      rethrow;
    }
  }

  Future<UserModel> register(String email, String password, String fullName) async {
    final response = await http.post(
      Uri.parse(ApiConfig.register),

      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
        'full_name': fullName,
      }),
    );

    if (response.statusCode == 200) {
      return UserModel.fromJson(jsonDecode(response.body));
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Registration failed');
    }
  }

  Future<void> _saveTokens(String access, String refresh) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', access);
    await prefs.setString('refresh_token', refresh);
  }

  Future<String?> getAccessToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }

  Future<Map<String, String>> getAuthHeaders() async {
    final token = await getAccessToken();
    return {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    };
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('refresh_token');
  }
}
