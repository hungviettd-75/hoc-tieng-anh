import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/learning_models.dart';

class LearnService {
  Future<LearningDashboardData> getDashboardData() async {
    final response = await http.get(Uri.parse('http://localhost:8000/api/v1/learn/dashboard'));
    if (response.statusCode == 200) {
      final jsonResponse = jsonDecode(response.body);
      return LearningDashboardData.fromJson(jsonResponse);
    } else {
      throw Exception('Failed to load learning dashboard');
    }
  }
}
