import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:animate_do/animate_do.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:ai_english_coach/core/api_config.dart';
import 'package:ai_english_coach/features/auth/services/auth_service.dart';

class VocabularyLeaderboardPage extends StatefulWidget {
  const VocabularyLeaderboardPage({super.key});

  @override
  State<VocabularyLeaderboardPage> createState() => _VocabularyLeaderboardPageState();
}

class _VocabularyLeaderboardPageState extends State<VocabularyLeaderboardPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  String _errorMessage = '';

  List<Map<String, dynamic>> _leaderboard = [];
  List<Map<String, dynamic>> _challenges = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
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

      // 1. Tải Leaderboard
      final leadRes = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/learn/vocabulary/leaderboard'),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      // 2. Tải Challenges
      final chalRes = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/learn/vocabulary/challenges'),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      if (leadRes.statusCode == 200 && chalRes.statusCode == 200) {
        setState(() {
          _leaderboard = List<Map<String, dynamic>>.from(jsonDecode(utf8.decode(leadRes.bodyBytes)));
          _challenges = List<Map<String, dynamic>>.from(jsonDecode(utf8.decode(chalRes.bodyBytes)));
          _isLoading = false;
        });
      } else {
        setState(() {
          _errorMessage = 'Không thể tải dữ liệu bảng xếp hạng.';
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
        title: const Text('Đấu trường từ vựng 🏆', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppColors.primary,
          labelColor: Colors.white,
          unselectedLabelColor: AppColors.textSecondary,
          tabs: const [
            Tab(text: 'Bảng xếp hạng'),
            Tab(text: 'Thử thách ngày'),
          ],
        ),
      ),
      body: SafeArea(
        child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
            : _errorMessage.isNotEmpty
                ? _buildErrorState()
                : TabBarView(
                    controller: _tabController,
                    children: [
                      _buildLeaderboardView(),
                      _buildChallengesView(),
                    ],
                  ),
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
            onPressed: _loadData,
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary),
            child: const Text('Thử lại', style: TextStyle(color: Colors.white)),
          )
        ],
      ),
    );
  }

  Widget _buildLeaderboardView() {
    if (_leaderboard.isEmpty) {
      return const Center(child: Text('Chưa có dữ liệu bảng xếp hạng.', style: TextStyle(color: AppColors.textSecondary)));
    }

    return ListView.builder(
      padding: const EdgeInsets.all(20),
      itemCount: _leaderboard.length,
      itemBuilder: (context, index) {
        final user = _leaderboard[index];
        final rank = user['rank'] ?? (index + 1);
        final isMe = user['is_current_user'] ?? false;
        
        Color rankColor = Colors.white30;
        Widget rankWidget = Text('$rank', style: const TextStyle(color: Colors.white54, fontSize: 16, fontWeight: FontWeight.bold));

        if (rank == 1) {
          rankColor = Colors.amber;
          rankWidget = const Icon(Icons.emoji_events_rounded, color: Colors.amber, size: 24);
        } else if (rank == 2) {
          rankColor = Colors.grey;
          rankWidget = const Icon(Icons.emoji_events_rounded, color: Colors.grey, size: 24);
        } else if (rank == 3) {
          rankColor = Colors.brown;
          rankWidget = const Icon(Icons.emoji_events_rounded, color: Colors.brown, size: 24);
        }

        return FadeInLeft(
          delay: Duration(milliseconds: 60 * index),
          child: Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: isMe ? AppColors.primary.withOpacity(0.12) : AppColors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isMe ? AppColors.primary : Colors.white.withOpacity(0.05),
                width: isMe ? 1.5 : 1,
              ),
            ),
            child: Row(
              children: [
                SizedBox(width: 30, child: Center(child: rankWidget)),
                const SizedBox(width: 12),
                CircleAvatar(
                  backgroundColor: AppColors.background,
                  radius: 20,
                  child: Text(user['name'][0].toUpperCase(), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user['name'],
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: isMe ? FontWeight.bold : FontWeight.w600,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text('Cấp độ ${user['level']}', style: const TextStyle(color: AppColors.textSecondary, fontSize: 11)),
                    ],
                  ),
                ),
                Text(
                  '${user['xp']} XP',
                  style: TextStyle(color: isMe ? AppColors.primary : AppColors.tertiary, fontWeight: FontWeight.bold, fontSize: 15),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildChallengesView() {
    if (_challenges.isEmpty) {
      return const Center(child: Text('Chưa có dữ liệu thử thách ngày.', style: TextStyle(color: AppColors.textSecondary)));
    }

    return ListView.builder(
      padding: const EdgeInsets.all(20),
      itemCount: _challenges.length,
      itemBuilder: (context, index) {
        final ch = _challenges[index];
        final isCompleted = ch['is_completed'] ?? false;
        final target = ch['target_value'] ?? 1;
        final current = ch['current_value'] ?? 0;
        final progress = (current as num) / (target as num);

        return FadeInUp(
          delay: Duration(milliseconds: 80 * index),
          child: Container(
            margin: const EdgeInsets.only(bottom: 16),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: isCompleted ? AppColors.success.withOpacity(0.3) : Colors.white.withOpacity(0.05),
                width: 1.5,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        ch['title'],
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: isCompleted ? AppColors.success.withOpacity(0.12) : AppColors.tertiary.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        isCompleted ? 'Đã hoàn thành' : 'Đang làm: $current/$target',
                        style: TextStyle(
                          color: isCompleted ? AppColors.success : AppColors.tertiary,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  ch['description'],
                  style: const TextStyle(color: AppColors.textSecondary, fontSize: 12, height: 1.4),
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '+${ch['xp_reward']} XP Thưởng 🎁',
                      style: const TextStyle(color: AppColors.success, fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                    if (isCompleted)
                      const Icon(Icons.check_circle_rounded, color: AppColors.success, size: 24),
                  ],
                ),
                if (!isCompleted) ...[
                  const SizedBox(height: 12),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: progress.clamp(0.0, 1.0),
                      backgroundColor: Colors.white.withOpacity(0.05),
                      valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
                      minHeight: 5,
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
