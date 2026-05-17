import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../providers/learn_provider.dart';
import '../widgets/skill_map_chart.dart';
import '../widgets/lesson_feed_card.dart';

class LearnPage extends ConsumerWidget {
  const LearnPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardDataAsync = ref.watch(learningDashboardProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () {
            if (Navigator.of(context).canPop()) {
              context.pop();
            } else {
              context.go('/');
            }
          },
        ),
        title: const Text(
          'Lộ trình cá nhân',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        actions: [],
      ),
      body: dashboardDataAsync.when(
        data: (data) {
          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(learningDashboardProvider);
            },
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Bản đồ kỹ năng',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Phân tích bằng AI về trình độ tiếng Anh hiện tại của bạn.',
                    style: TextStyle(color: Colors.white54, fontSize: 14),
                  ),
                  const SizedBox(height: 24),
                  
                  // Skill Map Radar Chart
                  Center(
                    child: SizedBox(
                      height: 250,
                      child: SkillMapChart(skillLevel: data.skillLevel),
                    ),
                  ),
                  
                  const SizedBox(height: 32),
                  
                  // Recommendations
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Bài học tiếp theo',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          'Đề xuất bởi AI',
                          style: TextStyle(
                            color: AppColors.primary,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  
                  if (data.recommendations.isEmpty)
                    const Center(
                      child: Padding(
                        padding: EdgeInsets.all(32.0),
                        child: Text(
                          'Bạn đã hoàn thành tất cả đề xuất cho hôm nay!',
                          style: TextStyle(color: Colors.white54),
                        ),
                      ),
                    )
                  else
                    ...data.recommendations.map((rec) => LessonFeedCard(
                          recommendation: rec,
                          onTap: () {
                            if (rec.contentType == 'roleplay') {
                              context.push('/voice-chat?mode=roleplay&topic=${Uri.encodeComponent(rec.topic)}');
                            } else if (rec.contentType == 'speaking') {
                              context.push('/voice-chat?mode=free_talk');
                            } else {
                              context.push('/learn/lesson', extra: rec);
                            }
                          },
                        )),
                ],
              ),
            ),
          );
        },
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppColors.primary),
        ),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, color: Colors.redAccent, size: 48),
              const SizedBox(height: 16),
              Text(
                'Tải dữ liệu thất bại',
                style: const TextStyle(color: Colors.white),
              ),
              TextButton(
                onPressed: () => ref.invalidate(learningDashboardProvider),
                child: const Text('Thử lại'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
