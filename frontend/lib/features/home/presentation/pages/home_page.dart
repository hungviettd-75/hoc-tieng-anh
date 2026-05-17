import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:ai_english_coach/features/home/presentation/providers/home_provider.dart';
import 'package:ai_english_coach/features/home/models/dashboard_model.dart';
import 'package:ai_english_coach/features/gamification/widgets/xp_progress_bar.dart';
import 'package:ai_english_coach/features/gamification/widgets/confetti_overlay.dart';
import 'package:ai_english_coach/features/gamification/providers/gamification_provider.dart';
import 'package:ai_english_coach/features/gamification/screens/leaderboard_screen.dart';
import 'package:ai_english_coach/features/gamification/screens/achievements_screen.dart';
import 'package:confetti/confetti.dart';


class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  late ConfettiController _confettiController;

  @override
  void initState() {
    super.initState();
    _confettiController = ConfettiController(duration: const Duration(seconds: 3));
  }

  @override
  void dispose() {
    _confettiController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final homeState = ref.watch(homeProvider);

    return ConfettiOverlay(
      controller: _confettiController,
      child: Scaffold(
        body: RefreshIndicator(
          onRefresh: () async {
            await ref.read(homeProvider.notifier).fetchStats();
            await ref.read(gamificationProvider.notifier).fetchStatus();
          },
          child: CustomScrollView(
            slivers: [
              _buildAppBar(context),
              SliverToBoxAdapter(
                child: homeState.when(
                  data: (stats) => _buildDashboardContent(context, stats),
                  loading: () => const Center(child: Padding(
                    padding: EdgeInsets.all(50.0),
                    child: CircularProgressIndicator(),
                  )),
                  error: (err, stack) => Center(child: Text('Error: $err')),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }


  Widget _buildAppBar(BuildContext context) {
    return SliverAppBar(
      expandedHeight: 120,
      floating: true,
      pinned: true,
      backgroundColor: AppColors.background,
      flexibleSpace: FlexibleSpaceBar(
        titlePadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        title: Row(
          children: [
            const Icon(Icons.bolt_rounded, color: AppColors.primary),
            const SizedBox(width: 8),
            Text('AI Coach', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
            const Spacer(),
          ],
        ),
      ),
    );
  }

  Widget _buildDashboardContent(BuildContext context, DashboardStats stats) {
    final gamificationState = ref.watch(gamificationProvider);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildGreetingSection(context, stats),
          const SizedBox(height: 24),
          gamificationState.when(
            data: (gStats) => XpProgressBar(currentXp: gStats.totalXp, level: gStats.level),
            loading: () => _buildXPProgress(context, stats.xp),
            error: (_, __) => _buildXPProgress(context, stats.xp),
          ),
          const SizedBox(height: 24),
          _buildGamificationActions(context),
          const SizedBox(height: 24),
          _buildStreakAndGoals(context, stats),
          const SizedBox(height: 24),
          _buildQuickActions(context),
          const SizedBox(height: 24),
          _buildContinueLearning(context, stats.recentActivity),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _buildGamificationActions(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _buildActionChip(
            'Bảng xếp hạng',
            Icons.leaderboard_rounded,
            Colors.amber,
            () => Navigator.push(context, MaterialPageRoute(builder: (_) => const LeaderboardScreen())),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildActionChip(
            'Thành tích',
            Icons.emoji_events_rounded,
            Colors.orange,
            () => Navigator.push(context, MaterialPageRoute(builder: (_) => const AchievementsScreen())),
          ),
        ),
      ],
    );
  }

  Widget _buildActionChip(String label, IconData icon, Color color, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withOpacity(0.2)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }


  Widget _buildGreetingSection(BuildContext context, DashboardStats stats) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('${stats.greeting}, ${stats.fullName} 👋', style: const TextStyle(fontSize: 16, color: AppColors.textSecondary)),
        const SizedBox(height: 8),
        Text(stats.motivation, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, height: 1.2)),
      ],
    );
  }

  Widget _buildXPProgress(BuildContext context, XPStats xp) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.primary.withOpacity(0.1)),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Cấp độ ${xp.level}', style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.primary)),
              Text('${xp.totalXp} / ${xp.nextLevelXp} XP', style: const TextStyle(color: AppColors.textSecondary)),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: LinearProgressIndicator(
              value: xp.totalXp / xp.nextLevelXp,
              minHeight: 8,
              backgroundColor: Colors.white.withOpacity(0.05),
              valueColor: const AlwaysStoppedAnimation(AppColors.primary),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStreakAndGoals(BuildContext context, DashboardStats stats) {
    return Row(
      children: [
        Expanded(
          flex: 4,
          child: _buildInfoCard(
            title: 'Streak',
            value: '${stats.streak.currentStreak}',
            subtitle: 'Days',
            icon: Icons.local_fire_department_rounded,
            iconColor: Colors.orange,
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          flex: 6,
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Mục tiêu hàng ngày', style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                const SizedBox(height: 12),
                ...stats.dailyGoals.map((goal) => Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Row(
                    children: [
                      Icon(_getGoalIcon(goal.goalType), size: 14, color: AppColors.primary),
                      const SizedBox(width: 8),
                      Expanded(
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: goal.currentValue / goal.targetValue,
                            minHeight: 4,
                            backgroundColor: Colors.white.withOpacity(0.05),
                            valueColor: const AlwaysStoppedAnimation(AppColors.primary),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text('${goal.currentValue}/${goal.targetValue}', style: const TextStyle(fontSize: 10)),
                    ],
                  ),
                )).toList(),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildInfoCard({required String title, required String value, required String subtitle, required IconData icon, required Color iconColor}) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: iconColor),
          const SizedBox(height: 12),
          Text(value, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
          Text(title, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Truy cập nhanh', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        SizedBox(
          height: 100,
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: [
              _buildActionItem(
                Icons.chat_bubble_rounded, 
                'Trò chuyện', 
                Colors.blue, 
                onTap: () => context.push('/chat'),
              ),
              _buildActionItem(
                Icons.mic_rounded, 
                'Luyện nói', 
                AppColors.primary,
                onTap: () => context.push('/voice-chat'),
              ),
              _buildActionItem(
                Icons.psychology_rounded, 
                'IELTS', 
                Colors.purple, 
                onTap: () => context.push('/ielts'),
              ),
              _buildActionItem(
                Icons.translate_rounded, 
                'Từ vựng', 
                Colors.orange, 
                onTap: () => context.push('/vocabulary-list'),
              ),
              _buildActionItem(
                Icons.groups_rounded, 
                'Nhập vai', 
                Colors.green, 
                onTap: () => context.push('/voice-chat'),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildActionItem(IconData icon, String label, Color color, {required VoidCallback onTap}) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          width: 90,
          margin: const EdgeInsets.only(right: 16),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: color.withOpacity(0.2)),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: color),
              const SizedBox(height: 8),
              Text(label, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContinueLearning(BuildContext context, List<String> activities) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('Tiếp tục học', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            TextButton(onPressed: () {}, child: const Text('Xem tất cả')),
          ],
        ),
        ...activities.map((act) => Material(
          color: Colors.transparent,
          child: Container(
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(16),
            ),
            child: InkWell(
              onTap: () {
                // Điều hướng dựa trên nội dung hoạt động
                final activity = act.toLowerCase();
                if (activity.contains('speaking') || activity.contains('phát âm')) {
                  context.go('/speaking');
                } else if (activity.contains('vocabulary') || activity.contains('từ vựng')) {
                  context.push('/vocabulary-list');
                } else {
                  context.push('/chat');
                }
              },
              borderRadius: BorderRadius.circular(16),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(color: AppColors.primary.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.play_arrow_rounded, color: AppColors.primary),
                    ),
                    const SizedBox(width: 16),
                    Expanded(child: Text(act, style: const TextStyle(fontWeight: FontWeight.bold))),
                    const Icon(Icons.chevron_right_rounded, color: AppColors.textSecondary),
                  ],
                ),
              ),
            ),
          ),
        )).toList(),
      ],
    );
  }

  IconData _getGoalIcon(String type) {
    switch (type) {
      case 'speaking': return Icons.mic_rounded;
      case 'vocabulary': return Icons.translate_rounded;
      default: return Icons.star_rounded;
    }
  }
}
