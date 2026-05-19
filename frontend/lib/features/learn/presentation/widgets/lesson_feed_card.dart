import 'package:flutter/material.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../../models/learning_models.dart';
import 'package:animate_do/animate_do.dart';

class LessonFeedCard extends StatelessWidget {
  final RecommendationItem recommendation;
  final VoidCallback onTap;

  const LessonFeedCard({
    super.key,
    required this.recommendation,
    required this.onTap,
  });

  IconData _getIcon() {
    switch (recommendation.contentType.toLowerCase()) {
      case 'grammar':
        return Icons.menu_book_rounded;
      case 'vocabulary':
        return Icons.translate_rounded;
      case 'speaking':
      case 'roleplay':
        return Icons.record_voice_over_rounded;
      case 'listening':
        return Icons.headphones_rounded;
      default:
        return Icons.school_rounded;
    }
  }

  Color _getColor() {
    switch (recommendation.contentType.toLowerCase()) {
      case 'grammar':
        return Colors.blueAccent;
      case 'vocabulary':
        return Colors.orangeAccent;
      case 'speaking':
      case 'roleplay':
        return Colors.greenAccent;
      case 'listening':
        return Colors.purpleAccent;
      default:
        return AppColors.primary;
    }
  }

  String _translateContentType(String contentType) {
    switch (contentType.toLowerCase()) {
      case 'grammar': return 'NGỮ PHÁP';
      case 'vocabulary': return 'TỪ VỰNG';
      case 'roleplay': return 'NHẬP VAI';
      case 'listening': return 'LUYỆN NGHE';
      case 'speaking': return 'LUYỆN NÓI';
      default: return contentType.toUpperCase();
    }
  }

  @override
  Widget build(BuildContext context) {
    return FadeInUp(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          margin: const EdgeInsets.only(bottom: 16),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.white10),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.2),
                blurRadius: 10,
                offset: const Offset(0, 5),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: _getColor().withOpacity(0.2),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        children: [
                          Icon(_getIcon(), size: 16, color: _getColor()),
                          const SizedBox(width: 6),
                          Text(
                            _translateContentType(recommendation.contentType),
                            style: TextStyle(
                              color: _getColor(),
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Row(
                      children: [
                        const Icon(Icons.timer_outlined, size: 14, color: Colors.white54),
                        const SizedBox(width: 4),
                        Text(
                          '${recommendation.estimatedMinutes} phút',
                          style: const TextStyle(color: Colors.white54, fontSize: 12),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  recommendation.topic,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  recommendation.description,
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.primary.withOpacity(0.3)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.auto_awesome, size: 16, color: AppColors.primary),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          recommendation.reason,
                          style: TextStyle(
                            color: AppColors.primary.withOpacity(0.9),
                            fontSize: 12,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
