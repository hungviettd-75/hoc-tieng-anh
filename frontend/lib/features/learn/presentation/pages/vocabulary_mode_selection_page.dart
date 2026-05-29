import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:animate_do/animate_do.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../providers/learn_provider.dart';

class VocabularyModeSelectionPage extends ConsumerWidget {
  final String level;
  final String words;

  const VocabularyModeSelectionPage({
    super.key,
    required this.level,
    required this.words,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => context.pop(),
        ),
        title: Text(
          'Chọn chế độ học - Trình độ $level',
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 20),
              FadeInDown(
                duration: const Duration(milliseconds: 600),
                child: Column(
                  children: [
                    Text(
                      'Bắt đầu học ngay thôi! 🚀',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w900,
                        foreground: Paint()
                          ..shader = AppColors.primaryGradient.createShader(
                            const Rect.fromLTWH(0.0, 0.0, 200.0, 70.0),
                          ),
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Hãy lựa chọn phương pháp học tập phù hợp nhất với bạn hôm nay nhé.',
                      style: TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 15,
                        height: 1.5,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 40),
              Expanded(
                child: Column(
                  children: [
                    // CARD 1 — LUYỆN ĐỌC
                    Expanded(
                      child: FadeInLeft(
                        duration: const Duration(milliseconds: 600),
                        delay: const Duration(milliseconds: 200),
                        child: _buildModeCard(
                          context: context,
                          ref: ref,
                          title: 'LUYỆN ĐỌC',
                          description: 'Nghe phát âm, luyện speaking, học câu ví dụ',
                          icon: Icons.menu_book_rounded,
                          color: AppColors.primary,
                          onTap: () {
                            // Lưu state
                            ref.read(selectedLevelProvider.notifier).state = level;
                            ref.read(learningModeProvider.notifier).state = 'reading';
                            
                            // Điều hướng đến chat mode luyện đọc cũ
                            context.push(
                              '/chat?mode=vocabulary_practice&level=$level&words=${Uri.encodeComponent(words)}',
                            );
                          },
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    // CARD 2 — LUYỆN GHÉP TỪ
                    Expanded(
                      child: FadeInRight(
                        duration: const Duration(milliseconds: 600),
                        delay: const Duration(milliseconds: 400),
                        child: _buildModeCard(
                          context: context,
                          ref: ref,
                          title: 'LUYỆN GHÉP TỪ',
                          description: 'Chọn nghĩa đúng, mini game từ vựng, luyện phản xạ',
                          icon: Icons.extension_rounded,
                          color: AppColors.secondary,
                          onTap: () {
                            // Lưu state
                            ref.read(selectedLevelProvider.notifier).state = level;
                            ref.read(learningModeProvider.notifier).state = 'matching';
                            
                            // Điều hướng đến game ghép từ
                            context.push(
                              '/vocabulary-matching-game?level=$level',
                            );
                          },
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 30),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildModeCard({
    required BuildContext context,
    required WidgetRef ref,
    required String title,
    required String description,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: LinearGradient(
          colors: [
            color.withOpacity(0.12),
            AppColors.surface.withOpacity(0.8),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.05),
            blurRadius: 15,
            offset: const Offset(0, 8),
          ),
        ],
        border: Border.all(
          color: color.withOpacity(0.2),
          width: 1.5,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(24),
          onTap: onTap,
          splashColor: color.withOpacity(0.1),
          highlightColor: color.withOpacity(0.05),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 20.0),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        decoration: BoxDecoration(
                          color: color.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          title,
                          style: TextStyle(
                            color: color,
                            fontWeight: FontWeight.w900,
                            fontSize: 13,
                            letterSpacing: 1.2,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        description,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          height: 1.4,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Text(
                            'Bắt đầu ngay',
                            style: TextStyle(
                              color: color,
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(width: 4),
                          Icon(
                            Icons.arrow_forward_rounded,
                            size: 16,
                            color: color,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: color.withOpacity(0.2),
                        blurRadius: 10,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: Icon(
                    icon,
                    size: 40,
                    color: color,
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
