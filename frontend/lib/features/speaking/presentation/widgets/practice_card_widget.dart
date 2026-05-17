import 'package:flutter/material.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../../models/pronunciation_models.dart';

/// Card hiển thị một sentence luyện tập.
class PracticeCardWidget extends StatelessWidget {
  final PracticeSentence sentence;
  final VoidCallback onTap;
  final VoidCallback? onListen;

  const PracticeCardWidget({
    super.key,
    required this.sentence,
    required this.onTap,
    this.onListen,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.05)),
        ),
        child: Row(
          children: [
            // Level badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: _getLevelColor(sentence.level).withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                sentence.level,
                style: TextStyle(
                  color: _getLevelColor(sentence.level),
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
            const SizedBox(width: 14),
            // Sentence text
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    sentence.text,
                    style: const TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _getCategoryLabel(sentence.category),
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            // Listen button
            if (onListen != null)
              IconButton(
                onPressed: onListen,
                icon: const Icon(Icons.volume_up_rounded, color: AppColors.primary, size: 22),
              ),
            // Arrow
            const Icon(Icons.chevron_right_rounded, color: AppColors.textSecondary),
          ],
        ),
      ),
    );
  }

  Color _getLevelColor(String level) {
    switch (level) {
      case 'A1':
        return AppColors.success;
      case 'A2':
        return const Color(0xFF10B981);
      case 'B1':
        return const Color(0xFFF59E0B);
      case 'B2':
        return const Color(0xFFEF4444);
      default:
        return AppColors.primary;
    }
  }

  String _getCategoryLabel(String category) {
    switch (category) {
      case 'greeting':
        return '👋 Chào hỏi';
      case 'daily':
        return '🏠 Đời sống';
      case 'travel':
        return '✈️ Du lịch';
      case 'business':
        return '💼 Công việc';
      case 'discussion':
        return '💬 Thảo luận';
      default:
        return '📝 Tổng quát';
    }
  }
}
