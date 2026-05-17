import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:animate_do/animate_do.dart';
import '../providers/speaking_provider.dart';
import '../widgets/practice_card_widget.dart';
import '../../models/pronunciation_models.dart';

/// Main Speaking hub - hiển thị trong bottom navigation tab "Speak".
class SpeakingPage extends ConsumerStatefulWidget {
  const SpeakingPage({super.key});

  @override
  ConsumerState<SpeakingPage> createState() => _SpeakingPageState();
}

class _SpeakingPageState extends ConsumerState<SpeakingPage> {
  String _selectedLevel = 'All';

  @override
  void initState() {
    super.initState();
    ref.read(speakingProvider.notifier).loadSentences();
    ref.read(speakingProvider.notifier).loadHistory();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(speakingProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            // AppBar with Back Button
            SliverAppBar(
              backgroundColor: Colors.transparent,
              elevation: 0,
              leading: IconButton(
                icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
                onPressed: () => context.go('/'),
              ),
              floating: true,
            ),
            // Header
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: FadeInDown(
                  duration: const Duration(milliseconds: 500),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Luyện nói',
                        style: TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Cải thiện phát âm với chấm điểm bằng AI',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            // Daily Challenge Card
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
                child: FadeInUp(
                  duration: const Duration(milliseconds: 600),
                  child: _buildDailyChallengeCard(),
                ),
              ),
            ),

            // Stats Row
            if (state.history != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                  child: FadeInUp(
                    delay: const Duration(milliseconds: 200),
                    child: _buildStatsRow(state.history!),
                  ),
                ),
              ),

            // Level Filter
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
                child: FadeInUp(
                  delay: const Duration(milliseconds: 300),
                  child: _buildLevelFilter(),
                ),
              ),
            ),

            // Sentence List
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final filtered = _getFilteredSentences(state.sentences);
                    if (index >= filtered.length) return null;
                    final sentence = filtered[index];

                    return FadeInUp(
                      delay: Duration(milliseconds: 100 * index),
                      child: PracticeCardWidget(
                        sentence: sentence,
                        onTap: () {
                          context.push('/speaking/practice', extra: sentence);
                        },
                        onListen: () {
                          ref.read(speakingProvider.notifier).playReference(sentence.text);
                        },
                      ),
                    );
                  },
                  childCount: _getFilteredSentences(state.sentences).length,
                ),
              ),
            ),

            // Bottom padding
            const SliverToBoxAdapter(child: SizedBox(height: 100)),
          ],
        ),
      ),
    );
  }

  Widget _buildDailyChallengeCard() {
    return GestureDetector(
      onTap: () {
        final sentences = ref.read(speakingProvider).sentences;
        if (sentences.isNotEmpty) {
          context.push('/speaking/practice', extra: sentences.first);
        }
      },
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF6366F1), Color(0xFF8B5CF6), Color(0xFFA855F7)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(
              color: AppColors.primary.withOpacity(0.3),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Text(
                      '🔥 Thử thách hàng ngày',
                      style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Luyện tập\nPhát âm',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Đạt trên 80 điểm để hoàn thành',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.8),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              width: 70,
              height: 70,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.mic_rounded, color: Colors.white, size: 36),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsRow(PronunciationHistory history) {
    return Row(
      children: [
        _buildStatItem('Lượt học', '${history.totalSessions}', Icons.timeline_rounded),
        const SizedBox(width: 12),
        _buildStatItem('Điểm TB', '${history.averageScore.toInt()}', Icons.star_rounded),
        const SizedBox(width: 12),
        _buildStatItem('Chuỗi ngày', '${history.totalSessions}', Icons.local_fire_department_rounded),
      ],
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.05)),
        ),
        child: Column(
          children: [
            Icon(icon, color: AppColors.primary, size: 22),
            const SizedBox(height: 6),
            Text(
              value,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            Text(
              label,
              style: TextStyle(color: AppColors.textSecondary, fontSize: 11),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLevelFilter() {
    final levels = ['Tất cả', 'A1', 'A2', 'B1', 'B2'];
    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: levels.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final level = levels[index];
          final isSelected = _selectedLevel == level;
          return GestureDetector(
            onTap: () {
              setState(() => _selectedLevel = level);
              if (level == 'Tất cả') {
                ref.read(speakingProvider.notifier).loadSentences();
              } else {
                ref.read(speakingProvider.notifier).loadSentences(level: level);
              }
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(horizontal: 20),
              decoration: BoxDecoration(
                color: isSelected ? AppColors.primary : AppColors.surface,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isSelected ? AppColors.primary : Colors.white10,
                ),
              ),
              alignment: Alignment.center,
              child: Text(
                level,
                style: TextStyle(
                  color: isSelected ? Colors.white : AppColors.textSecondary,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                  fontSize: 13,
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  List<dynamic> _getFilteredSentences(List<dynamic> sentences) {
    if (_selectedLevel == 'Tất cả') return sentences;
    return sentences.where((s) => s.level == _selectedLevel).toList();
  }
}
