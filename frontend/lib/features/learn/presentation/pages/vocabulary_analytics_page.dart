import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:animate_do/animate_do.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:ai_english_coach/core/api_config.dart';
import 'package:ai_english_coach/features/auth/services/auth_service.dart';

class VocabularyAnalyticsPage extends StatefulWidget {
  const VocabularyAnalyticsPage({super.key});

  @override
  State<VocabularyAnalyticsPage> createState() => _VocabularyAnalyticsPageState();
}

class _VocabularyAnalyticsPageState extends State<VocabularyAnalyticsPage> {
  bool _isLoading = true;
  String _errorMessage = '';
  Map<String, dynamic> _data = {};

  @override
  void initState() {
    super.initState();
    _fetchAnalytics();
  }

  Future<void> _fetchAnalytics() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final token = await AuthService().getAccessToken();
      final headers = {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

      final response = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/learn/vocabulary/analytics'),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        setState(() {
          _data = jsonDecode(utf8.decode(response.bodyBytes));
          _isLoading = false;
        });
      } else {
        setState(() {
          _errorMessage = 'Không thể tải dữ liệu phân tích từ server.';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Lỗi kết nối. Vui lòng kiểm tra lại mạng!';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => context.pop(),
        ),
        title: const Text('Phân tích từ vựng AI', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
      body: SafeArea(
        child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
            : _errorMessage.isNotEmpty
                ? _buildErrorState()
                : _buildAnalyticsDashboard(),
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.cloud_off_rounded, size: 64, color: Colors.white24),
          const SizedBox(height: 16),
          Text(_errorMessage, style: const TextStyle(color: Colors.white54, fontSize: 15)),
          const SizedBox(height: 12),
          ElevatedButton(
            onPressed: _fetchAnalytics,
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary),
            child: const Text('Thử lại', style: TextStyle(color: Colors.white)),
          )
        ],
      ),
    );
  }

  Widget _buildAnalyticsDashboard() {
    final accuracy = _data['accuracy'] ?? 100.0;
    final totalAttempts = _data['total_attempts'] ?? 0;
    final weakList = List<Map<String, dynamic>>.from(_data['weak_vocabulary'] ?? []);
    final masteredList = List<Map<String, dynamic>>.from(_data['mastered_vocabulary'] ?? []);
    final spacedRep = _data['spaced_repetition'] ?? {};
    final overdueCount = spacedRep['overdue_count'] ?? 0;
    final upcomingCount = spacedRep['upcoming_count'] ?? 0;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Accuracy Card (Thẻ tỷ lệ chính xác)
          FadeInDown(
            child: _buildAccuracyCard(accuracy, totalAttempts),
          ),
          const SizedBox(height: 20),

          // 2. Spaced Repetition Info
          FadeInDown(
            delay: const Duration(milliseconds: 100),
            child: _buildSpacedRepetitionCard(overdueCount, upcomingCount),
          ),
          const SizedBox(height: 24),

          // 3. Danh sách từ vựng yếu (Weak Vocabulary)
          FadeInUp(
            delay: const Duration(milliseconds: 200),
            child: _buildSectionTitle('Từ vựng cần cải thiện (Từ yếu) ⚠️'),
          ),
          const SizedBox(height: 8),
          FadeInUp(
            delay: const Duration(milliseconds: 300),
            child: weakList.isEmpty
                ? _buildEmptySection('Tuyệt vời! Bạn không có từ vựng yếu nào.')
                : Column(
                    children: weakList.map((item) => _buildWeakWordTile(item)).toList(),
                  ),
          ),
          const SizedBox(height: 24),

          // 4. Danh sách từ đã thuộc (Mastered Vocabulary)
          FadeInUp(
            delay: const Duration(milliseconds: 400),
            child: _buildSectionTitle('Từ vựng đã làm chủ (Đã thuộc) ✅'),
          ),
          const SizedBox(height: 8),
          FadeInUp(
            delay: const Duration(milliseconds: 500),
            child: masteredList.isEmpty
                ? _buildEmptySection('Hãy tiếp tục ôn tập để đưa các từ vựng vào bộ nhớ dài hạn nhé!')
                : Column(
                    children: masteredList.map((item) => _buildMasteredWordTile(item)).toList(),
                  ),
          ),
          const SizedBox(height: 30),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
    );
  }

  Widget _buildEmptySection(String message) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Center(
        child: Text(
          message,
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }

  Widget _buildAccuracyCard(double accuracy, int total) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: AppColors.primaryGradient,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withOpacity(0.3),
            blurRadius: 15,
            offset: const Offset(0, 8),
          )
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Tỉ lệ chính xác',
                  style: TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.w500),
                ),
                const SizedBox(height: 8),
                Text(
                  '$accuracy%',
                  style: const TextStyle(color: Colors.white, fontSize: 36, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 8),
                Text(
                  'Tổng số câu đã làm: $total',
                  style: const TextStyle(color: Colors.white60, fontSize: 12),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: Colors.white.withOpacity(0.15), shape: BoxShape.circle),
            child: const Icon(Icons.stars_rounded, color: Colors.white, size: 44),
          ),
        ],
      ),
    );
  }

  Widget _buildSpacedRepetitionCard(int overdue, int upcoming) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Trí nhớ lặp lại ngắt quãng (Spaced Repetition)', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildRepSubCol('🔄 CẦN ÔN TẬP', '$overdue từ', AppColors.tertiary),
              ),
              Container(width: 1.5, height: 40, color: Colors.white10),
              Expanded(
                child: _buildRepSubCol('📅 ĐÃ GHI NHỚ', '$upcoming từ', AppColors.success),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildRepSubCol(String label, String value, Color color) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 11, fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        Text(value, style: TextStyle(color: color, fontSize: 18, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildWeakWordTile(Map<String, dynamic> item) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            item['word'],
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: AppColors.error.withOpacity(0.12), borderRadius: BorderRadius.circular(8)),
            child: Text(
              'Sai ${item['error_count']} lần ⚠️',
              style: const TextStyle(color: AppColors.error, fontSize: 11, fontWeight: FontWeight.bold),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildMasteredWordTile(Map<String, dynamic> item) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            item['word'],
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: AppColors.success.withOpacity(0.12), borderRadius: BorderRadius.circular(8)),
            child: Text(
              'Đúng liên tiếp: ${item['correct_streak']} 🔥',
              style: const TextStyle(color: AppColors.success, fontSize: 11, fontWeight: FontWeight.bold),
            ),
          )
        ],
      ),
    );
  }
}
