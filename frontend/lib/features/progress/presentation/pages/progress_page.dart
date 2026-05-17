import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../widgets/ai_memory_insights_widget.dart';

class ProgressPage extends StatelessWidget {
  const ProgressPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Tiến độ & Phân tích'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => context.go('/'),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const AIMemoryInsightsWidget(userId: 1),
          const SizedBox(height: 30),
          
          // Section: Speaking Quality
          _buildSectionHeader('Chất lượng nói', Icons.mic_external_on_rounded, '+15% tuần này'),
          const SizedBox(height: 16),
          _buildSpeakingScoreCard(),
          const SizedBox(height: 16),
          _buildSimpleBarChart(),
          
          const SizedBox(height: 40),
          
          // Section: Vocabulary Growth
          _buildSectionHeader('Tăng trưởng từ vựng', Icons.auto_stories_rounded, '42 từ mới'),
          const SizedBox(height: 16),
          _buildVocabularyList(),
          
          const SizedBox(height: 30),
          _buildActionCard(context),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title, IconData icon, String trend) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(color: AppColors.primary.withOpacity(0.1), borderRadius: BorderRadius.circular(10)),
              child: Icon(icon, color: AppColors.primary, size: 20),
            ),
            const SizedBox(width: 12),
            Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          ],
        ),
        Text(trend, style: const TextStyle(color: Colors.greenAccent, fontSize: 13, fontWeight: FontWeight.w600)),
      ],
    );
  }

  Widget _buildSpeakingScoreCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [AppColors.surface, AppColors.surface.withOpacity(0.5)]),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Row(
        children: [
          _buildCircularScore(7.8),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Điểm lưu loát', style: TextStyle(color: Colors.white70, fontSize: 14)),
                const SizedBox(height: 4),
                const Text('Rất tốt', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
                const SizedBox(height: 8),
                Text(
                  'Bạn phát âm rõ ràng hơn 80% học viên khác.',
                  style: TextStyle(color: Colors.white38, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCircularScore(double score) {
    return Stack(
      alignment: Alignment.center,
      children: [
        SizedBox(
          height: 70, width: 70,
          child: CircularProgressIndicator(
            value: score / 10,
            strokeWidth: 8,
            backgroundColor: Colors.white10,
            color: AppColors.primary,
          ),
        ),
        Text(
          score.toString(),
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  Widget _buildSimpleBarChart() {
    final values = [0.4, 0.6, 0.5, 0.8, 0.7, 0.9, 0.85];
    final days = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
    
    return Container(
      height: 180,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        children: [
          Expanded(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: List.generate(values.length, (index) => Column(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Container(
                    width: 15,
                    height: 100 * values[index],
                    decoration: BoxDecoration(
                      color: index == 5 ? AppColors.primary : AppColors.primary.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(days[index], style: const TextStyle(color: Colors.white38, fontSize: 10)),
                ],
              )),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVocabularyList() {
    final words = [
      {'word': 'Incentive', 'meaning': 'Khuyến khích', 'status': 'Mastered'},
      {'word': 'Collaborate', 'meaning': 'Hợp tác', 'status': 'Learning'},
      {'word': 'Substantial', 'meaning': 'Đáng kể', 'status': 'New'},
    ];

    return Column(
      children: words.map((item) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: Colors.white.withOpacity(0.05), borderRadius: BorderRadius.circular(12)),
              child: const Icon(Icons.menu_book_rounded, color: AppColors.primary, size: 18),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item['word']!, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  Text(item['meaning']!, style: const TextStyle(color: Colors.white38, fontSize: 12)),
                ],
              ),
            ),
            _buildStatusBadge(item['status']!),
          ],
        ),
      )).toList(),
    );
  }

  Widget _buildStatusBadge(String status) {
    Color color = Colors.blue;
    String text = 'Mới';
    if (status == 'Mastered') { color = Colors.green; text = 'Đã thuộc'; }
    if (status == 'Learning') { color = Colors.orange; text = 'Đang học'; }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
      child: Text(text, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold)),
    );
  }

  Widget _buildActionCard(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.1),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.primary.withOpacity(0.2)),
      ),
      child: Column(
        children: [
          const Text(
            'Bạn đang làm rất tốt!',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.primary),
          ),
          const SizedBox(height: 8),
          const Text(
            'Hãy tiếp tục duy trì chuỗi học tập 12 ngày để đạt kết quả tốt nhất.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 13),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () => context.go('/speaking'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('Luyện tập ngay'),
          ),
        ],
      ),
    );
  }
}
