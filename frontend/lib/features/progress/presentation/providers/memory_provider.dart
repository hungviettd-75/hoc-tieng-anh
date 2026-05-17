import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../../models/memory_insight_model.dart';

final memoryInsightsProvider = FutureProvider.family<MemoryInsight, int>((ref, userId) async {
  // Thực tế nên lấy baseUrl từ một config service
  final response = await http.get(Uri.parse('http://127.0.0.1:8000/api/v1/memory/insights/$userId'));

  if (response.statusCode == 200) {
    return MemoryInsight.fromJson(json.decode(response.body));
  } else {
    throw Exception('Failed to load memory insights');
  }
});
