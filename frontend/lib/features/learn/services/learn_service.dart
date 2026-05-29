import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:ai_english_coach/core/api_config.dart';
import 'package:ai_english_coach/features/auth/services/auth_service.dart';
import '../models/learning_models.dart';

class LearnService {
  final AuthService _authService;

  LearnService(this._authService);

  Future<LearningDashboardData> getDashboardData() async {
    final token = await _authService.getAccessToken();
    final headers = {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };

    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/learn/dashboard'),
      headers: headers,
    );
    if (response.statusCode == 200) {
      final jsonResponse = jsonDecode(response.body);
      return LearningDashboardData.fromJson(jsonResponse);
    } else {
      throw Exception('Failed to load learning dashboard');
    }
  }

  Future<void> updatePreferences({int? dailyTimeGoalMinutes, String? targetLevel}) async {
    final token = await _authService.getAccessToken();
    final headers = {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };

    final body = jsonEncode({
      if (dailyTimeGoalMinutes != null) 'daily_time_goal_minutes': dailyTimeGoalMinutes,
      if (targetLevel != null) 'target_level': targetLevel,
    });

    final response = await http.put(
      Uri.parse('${ApiConfig.baseUrl}/learn/preferences'),
      headers: headers,
      body: body,
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to update learning preferences');
    }
  }
}
