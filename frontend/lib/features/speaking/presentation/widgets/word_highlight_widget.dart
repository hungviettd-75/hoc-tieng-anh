import 'package:flutter/material.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../../models/pronunciation_models.dart';

/// Widget hiển thị word-by-word comparison.
/// Từ đúng = xanh, từ sai = đỏ, từ gần đúng = vàng.
class WordHighlightWidget extends StatelessWidget {
  final List<WordScore> wordScores;

  const WordHighlightWidget({super.key, required this.wordScores});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 6,
      runSpacing: 8,
      children: wordScores.map((ws) => _buildWordChip(ws)).toList(),
    );
  }

  Widget _buildWordChip(WordScore ws) {
    Color bgColor;
    Color textColor;
    IconData? icon;

    if (ws.isCorrect) {
      bgColor = AppColors.success.withOpacity(0.15);
      textColor = AppColors.success;
      icon = Icons.check_circle_rounded;
    } else if (ws.confidence > 0.5) {
      bgColor = const Color(0xFFF59E0B).withOpacity(0.15);
      textColor = const Color(0xFFF59E0B);
      icon = Icons.warning_rounded;
    } else {
      bgColor = AppColors.error.withOpacity(0.15);
      textColor = AppColors.error;
      icon = Icons.cancel_rounded;
    }

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: textColor.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: textColor),
          const SizedBox(width: 4),
          Text(
            ws.word,
            style: TextStyle(
              color: textColor,
              fontWeight: FontWeight.w600,
              fontSize: 15,
            ),
          ),
        ],
      ),
    );
  }
}
