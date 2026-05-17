import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import '../features/speaking/models/pronunciation_models.dart';
import 'package:ai_english_coach/core/api_config.dart';


/// HTTP Service cho Speaking API endpoints.
class SpeakingService {
  static const String _baseUrl = ApiConfig.speaking;


  /// Upload audio + target text → nhận pronunciation scores.
  Future<PronunciationResult> analyzePronunciation({
    required Uint8List audioBytes,
    required String targetText,
    int userId = 1,
    String filename = 'recording.m4a',
  }) async {
    final uri = Uri.parse('$_baseUrl/analyze');
    final request = http.MultipartRequest('POST', uri);
    
    request.files.add(http.MultipartFile.fromBytes(
      'audio',
      audioBytes,
      filename: filename,
    ));
    request.fields['target_text'] = targetText;
    request.fields['user_id'] = userId.toString();

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      return PronunciationResult.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to analyze pronunciation: ${response.statusCode}');
    }
  }

  /// Lấy danh sách câu luyện tập.
  Future<List<PracticeSentence>> getSentences({String? level, String? category}) async {
    String url = '$_baseUrl/sentences';
    final params = <String, String>{};
    if (level != null) params['level'] = level;
    if (category != null) params['category'] = category;
    
    if (params.isNotEmpty) {
      url += '?${params.entries.map((e) => '${e.key}=${e.value}').join('&')}';
    }

    final response = await http.get(Uri.parse(url));
    if (response.statusCode == 200) {
      final list = jsonDecode(response.body) as List;
      return list.map((e) => PracticeSentence.fromJson(e)).toList();
    }
    throw Exception('Failed to load sentences: ${response.statusCode}');
  }

  /// Lấy lịch sử pronunciation.
  Future<PronunciationHistory> getHistory(int userId) async {
    final response = await http.get(Uri.parse('$_baseUrl/history/$userId'));
    if (response.statusCode == 200) {
      return PronunciationHistory.fromJson(jsonDecode(response.body));
    }
    throw Exception('Failed to load history: ${response.statusCode}');
  }
}
