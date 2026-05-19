import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:ai_english_coach/core/api_config.dart';
import '../../models/memory_insight_model.dart';

final memoryInsightsProvider = FutureProvider.family<MemoryInsight, int>((ref, userId) async {
  // Lấy baseUrl từ ApiConfig
  final response = await http.get(Uri.parse('${ApiConfig.baseUrl}/memory/insights/$userId'));

  if (response.statusCode == 200) {
    return MemoryInsight.fromJson(json.decode(response.body));
  } else {
    throw Exception('Failed to load memory insights');
  }
});
