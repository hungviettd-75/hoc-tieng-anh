import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:animate_do/animate_do.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:ai_english_coach/core/api_config.dart';
import 'package:ai_english_coach/features/auth/services/auth_service.dart';

class VocabularyTopicsPage extends StatefulWidget {
  const VocabularyTopicsPage({super.key});

  @override
  State<VocabularyTopicsPage> createState() => _VocabularyTopicsPageState();
}

class _VocabularyTopicsPageState extends State<VocabularyTopicsPage> {
  bool _isLoading = true;
  String _errorMessage = '';
  List<Map<String, dynamic>> _topics = [];

  @override
  void initState() {
    super.initState();
    _fetchTopics();
  }

  Future<void> _fetchTopics() async {
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
        Uri.parse('${ApiConfig.baseUrl}/learn/vocabulary/topics'),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        setState(() {
          _topics = data.map((item) => Map<String, dynamic>.from(item)).toList();
          _isLoading = false;
        });
      } else {
        setState(() {
          _errorMessage = 'Không thể tải danh sách chủ đề từ vựng.';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Lỗi kết nối. Vui lòng kiểm tra mạng!';
        _isLoading = false;
      });
    }
  }

  IconData _getIconData(String name) {
    switch (name) {
      case 'flight_takeoff_rounded': return Icons.flight_takeoff_rounded;
      case 'devices_other_rounded': return Icons.devices_other_rounded;
      case 'psychology_rounded': return Icons.psychology_rounded;
      case 'campaign_rounded': return Icons.campaign_rounded;
      case 'work_outline_rounded': return Icons.work_outline_rounded;
      case 'business_center_rounded': return Icons.business_center_rounded;
      case 'sports_soccer_rounded': return Icons.sports_soccer_rounded;
      case 'music_note_rounded': return Icons.music_note_rounded;
      case 'medical_services_rounded': return Icons.medical_services_rounded;
      case 'restaurant_menu_rounded': return Icons.restaurant_menu_rounded;
      case 'code_rounded': return Icons.code_rounded;
      case 'record_voice_over_rounded': return Icons.record_voice_over_rounded;
      case 'account_balance_wallet_rounded': return Icons.account_balance_wallet_rounded;
      case 'checkroom_rounded': return Icons.checkroom_rounded;
      case 'share_rounded': return Icons.share_rounded;
      default: return Icons.translate_rounded;
    }
  }

  Color _getTopicColor(int index) {
    final colors = [
      AppColors.primary,
      AppColors.secondary,
      AppColors.tertiary,
      Colors.teal,
      Colors.cyan,
      Colors.pinkAccent,
      Colors.amber,
      Colors.orange,
      Colors.indigo,
      Colors.deepOrange,
      Colors.lightGreen,
      Colors.purpleAccent,
      Colors.blue,
      Colors.redAccent,
      Colors.purple,
    ];
    return colors[index % colors.length];
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
        title: const Text('Kho từ vựng thông minh', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.emoji_events_rounded, color: Colors.amber, size: 24),
            tooltip: 'Đấu trường từ vựng',
            onPressed: () => context.push('/vocabulary-leaderboard'),
          ),
          IconButton(
            icon: const Icon(Icons.analytics_outlined, color: Colors.white, size: 24),
            tooltip: 'Phân tích từ vựng AI',
            onPressed: () => context.push('/vocabulary-analytics'),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
            : _errorMessage.isNotEmpty
                ? _buildErrorState()
                : _buildTopicsGrid(),
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
            onPressed: _fetchTopics,
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary),
            child: const Text('Thử lại', style: TextStyle(color: Colors.white)),
          )
        ],
      ),
    );
  }

  Widget _buildTopicsGrid() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 10),
        FadeInDown(
          child: const Text(
            'Chọn chủ đề bạn muốn học 📚',
            style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Mỗi chủ đề có từ vựng thích ứng tự động theo trình độ của bạn.',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 20),
        Expanded(
          child: GridView.builder(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              crossAxisSpacing: 14,
              mainAxisSpacing: 14,
              childAspectRatio: 0.95,
            ),
            itemCount: _topics.length,
            itemBuilder: (context, index) {
              final topic = _topics[index];
              final color = _getTopicColor(index);
              final progress = topic['progress'] ?? {};
              final percentage = progress['percentage'] ?? 0.0;
              final mastered = progress['mastered_count'] ?? 0;
              final total = progress['total_count'] ?? 10;

              return FadeInUp(
                delay: Duration(milliseconds: 60 * index),
                child: Container(
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: color.withOpacity(0.12), width: 1.5),
                  ),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(20),
                      onTap: () {
                        context.push(
                          '/vocabulary-topic-detail?code=${topic['code']}&name=${Uri.encodeComponent(topic['name'])}',
                        );
                      },
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: color.withOpacity(0.15),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                _getIconData(topic['icon']),
                                color: color,
                                size: 24,
                              ),
                            ),
                            const Spacer(),
                            Text(
                              topic['name'],
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              topic['description'],
                              style: const TextStyle(color: AppColors.textSecondary, fontSize: 10, height: 1.3),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const Spacer(),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  '$mastered/$total từ',
                                  style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold),
                                ),
                                Text(
                                  '$percentage%',
                                  style: const TextStyle(color: Colors.white60, fontSize: 11),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: (percentage as num) / 100.0,
                                backgroundColor: Colors.white.withOpacity(0.05),
                                valueColor: AlwaysStoppedAnimation<Color>(color),
                                minHeight: 4,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
