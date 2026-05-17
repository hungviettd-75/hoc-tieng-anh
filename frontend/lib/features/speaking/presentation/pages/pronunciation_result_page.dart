import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:animate_do/animate_do.dart';
import '../../models/pronunciation_models.dart';
import '../providers/speaking_provider.dart';
import '../widgets/score_radar_chart.dart';
import '../widgets/word_highlight_widget.dart';

class PronunciationResultPage extends ConsumerWidget {
  final PronunciationResult result;
  const PronunciationResultPage({super.key, required this.result});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close, color: Colors.white),
          onPressed: () {
            ref.read(speakingProvider.notifier).reset();
            context.go('/speaking');
          },
        ),
        title: const Text('Kết quả',
            style: TextStyle(color: AppColors.textPrimary, fontSize: 18, fontWeight: FontWeight.w600)),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          children: [
            const SizedBox(height: 16),
            // Overall Score Circle
            _buildOverallScore(),
            const SizedBox(height: 24),
            // Metric Bars
            _buildMetricBars(),
            const SizedBox(height: 24),
            // Radar Chart
            _buildRadarSection(),
            const SizedBox(height: 24),
            // Word Comparison
            _buildWordSection(),
            const SizedBox(height: 24),
            // AI Feedback
            _buildFeedbackCard(),
            const SizedBox(height: 24),
            // Action Buttons
            _buildActions(context, ref),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildOverallScore() {
    final score = result.overallScore;
    final color = _getScoreColor(score);
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(children: [
        _AnimatedScoreCircle(score: score, color: color),
        const SizedBox(height: 12),
        Text(_getScoreLabel(score),
            style: TextStyle(color: color, fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        Text('Điểm tổng quan', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
      ]),
    );
  }

  Widget _buildMetricBars() {
    final metrics = [
      ('🗣️ Trôi chảy', result.fluencyScore),
      ('🔤 Phát âm', result.pronunciationScore),
      ('💪 Tự tin', result.confidenceScore),
      ('🎵 Ngữ điệu', result.intonationScore),
    ];
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Chi tiết điểm số',
              style: TextStyle(color: AppColors.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          ...metrics.map((m) => _buildMetricBar(m.$1, m.$2)),
        ],
      ),
    );
  }

  Widget _buildMetricBar(String label, double score) {
    final color = _getScoreColor(score);
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        children: [
          Row(children: [
            Text(label, style: const TextStyle(color: AppColors.textPrimary, fontSize: 14)),
            const Spacer(),
            Text('${score.clamp(0, 100).toInt()}',
                style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16)),
          ]),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: score / 100),
              duration: const Duration(milliseconds: 1000),
              curve: Curves.easeOutCubic,
              builder: (context, value, _) => LinearProgressIndicator(
                value: value,
                minHeight: 8,
                backgroundColor: Colors.white.withOpacity(0.05),
                valueColor: AlwaysStoppedAnimation(color),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRadarSection() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(children: [
        const Text('Biểu đồ kỹ năng',
            style: TextStyle(color: AppColors.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        Center(
          child: ScoreRadarChart(
            fluency: result.fluencyScore,
            pronunciation: result.pronunciationScore,
            confidence: result.confidenceScore,
            intonation: result.intonationScore,
            size: 220,
          ),
        ),
      ]),
    );
  }

  Widget _buildWordSection() {
    if (result.wordScores.isEmpty) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Phân tích từ vựng',
              style: TextStyle(color: AppColors.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Text('Câu mẫu: "${result.targetText}"',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
          if (result.transcribedText.isNotEmpty)
            Text('Bạn đã nói: "${result.transcribedText}"',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
          const SizedBox(height: 14),
          WordHighlightWidget(wordScores: result.wordScores),
        ],
      ),
    );
  }

  Widget _buildFeedbackCard() {
    if (result.feedback.isEmpty) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [
          AppColors.primary.withOpacity(0.1),
          AppColors.secondary.withOpacity(0.1),
        ]),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.primary.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(children: [
            Icon(Icons.lightbulb_rounded, color: Color(0xFFF59E0B), size: 20),
            SizedBox(width: 8),
            Text('Nhận xét từ AI Coach',
                style: TextStyle(color: AppColors.textPrimary, fontSize: 15, fontWeight: FontWeight.w600)),
          ]),
          const SizedBox(height: 10),
          Text(result.feedback,
              style: const TextStyle(color: AppColors.textPrimary, fontSize: 14, height: 1.5)),
        ],
      ),
    );
  }

  Widget _buildActions(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Row(children: [
      Expanded(
        child: GestureDetector(
          onTap: () {
            ref.read(speakingProvider.notifier).reset();
            context.pop();
          },
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white10),
            ),
            child: const Center(
              child: Text('Luyện lại',
                  style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600, fontSize: 15)),
            ),
          ),
        ),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: GestureDetector(
          onTap: () {
            ref.read(speakingProvider.notifier).reset();
            context.go('/speaking');
          },
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 16),
            decoration: BoxDecoration(
              gradient: AppColors.primaryGradient,
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Center(
              child: Text('Câu tiếp theo',
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 15)),
            ),
          ),
        ),
      ),
      ]),
    );
  }

  Color _getScoreColor(double score) {
    if (score >= 70) return AppColors.success;
    if (score >= 40) return const Color(0xFFF59E0B);
    return AppColors.error;
  }

  String _getScoreLabel(double score) {
    if (score >= 90) return 'Excellent! 🌟';
    if (score >= 70) return 'Great Job! 👏';
    if (score >= 50) return 'Good Effort! 💪';
    if (score >= 30) return 'Keep Practicing! 📚';
    return 'Try Again! 🔄';
  }
}

/// Animated score circle widget
class _AnimatedScoreCircle extends StatefulWidget {
  final double score;
  final Color color;
  const _AnimatedScoreCircle({required this.score, required this.color});

  @override
  State<_AnimatedScoreCircle> createState() => _AnimatedScoreCircleState();
}

class _AnimatedScoreCircleState extends State<_AnimatedScoreCircle>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500));
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic);
    _ctrl.forward();
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (context, _) {
        final val = widget.score * _anim.value;
        return SizedBox(
          width: 140, height: 140,
          child: Stack(alignment: Alignment.center, children: [
            SizedBox(
              width: 140, height: 140,
              child: CircularProgressIndicator(
                value: val / 100,
                strokeWidth: 10,
                backgroundColor: Colors.white.withOpacity(0.05),
                valueColor: AlwaysStoppedAnimation(widget.color),
                strokeCap: StrokeCap.round,
              ),
            ),
            Text('${val.clamp(0, 100).toInt()}',
                style: TextStyle(
                    color: widget.color, fontSize: 42, fontWeight: FontWeight.bold)),
          ]),
        );
      },
    );
  }
}
