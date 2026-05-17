import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:animate_do/animate_do.dart';
import '../../models/learning_models.dart';
import '../providers/learn_provider.dart';

class LessonDetailPage extends ConsumerStatefulWidget {
  final RecommendationItem recommendation;

  const LessonDetailPage({super.key, required this.recommendation});

  @override
  ConsumerState<LessonDetailPage> createState() => _LessonDetailPageState();
}

class _LessonDetailPageState extends ConsumerState<LessonDetailPage> {
  bool _isCompleted = false;
  bool _isLoading = false;

  Future<void> _completeLesson() async {
    setState(() => _isLoading = true);
    try {
      // In a real app, this would call the service
      // await ref.read(learnServiceProvider).completeLesson(widget.recommendation.id);
      
      // Simulate API call delay
      await Future.delayed(const Duration(seconds: 1));
      
      if (mounted) {
        setState(() {
          _isCompleted = true;
          _isLoading = false;
        });
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Lesson "${widget.recommendation.topic}" completed! Skill boosted.'),
            backgroundColor: Colors.green,
          ),
        );
        
        // Invalidate dashboard to refresh skill map
        ref.invalidate(learningDashboardProvider);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.redAccent),
        );
      }
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
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          onPressed: () => context.pop(),
        ),
        title: Text(widget.recommendation.contentType.toUpperCase(), 
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 2)),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            FadeInDown(
              child: Text(
                widget.recommendation.topic,
                style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
            const SizedBox(height: 16),
            FadeInLeft(
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white10),
                ),
                child: Column(
                  children: [
                    _buildInfoRow(Icons.timer_outlined, 'Duration', '${widget.recommendation.estimatedMinutes} minutes'),
                    const Divider(color: Colors.white12, height: 24),
                    _buildInfoRow(Icons.bolt_rounded, 'Difficulty', widget.recommendation.difficultyLevel),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 32),
            const Text(
              'What you will learn',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 12),
            Text(
              widget.recommendation.description,
              style: const TextStyle(fontSize: 16, color: Colors.white70, height: 1.5),
            ),
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.primary.withOpacity(0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.auto_awesome, color: AppColors.primary, size: 20),
                      const SizedBox(width: 8),
                      const Text(
                        'AI Recommendation Reason',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    widget.recommendation.reason,
                    style: TextStyle(color: Colors.white.withOpacity(0.8), fontSize: 14),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 48),
            Center(
              child: _isCompleted 
                ? Column(
                    children: [
                      const Icon(Icons.check_circle_rounded, color: Colors.greenAccent, size: 64),
                      const SizedBox(height: 16),
                      const Text('Lesson Completed!', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      TextButton(
                        onPressed: () => context.pop(),
                        child: const Text('Back to Dashboard'),
                      ),
                    ],
                  )
                : SizedBox(
                    width: double.infinity,
                    height: 56,
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : _completeLesson,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        elevation: 4,
                      ),
                      child: _isLoading 
                        ? const CircularProgressIndicator(color: Colors.white)
                        : const Text('Mark as Completed', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    ),
                  ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, color: AppColors.primary, size: 20),
        const SizedBox(width: 12),
        Text(label, style: const TextStyle(color: Colors.white54, fontSize: 14)),
        const Spacer(),
        Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
      ],
    );
  }
}
