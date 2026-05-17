import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:animate_do/animate_do.dart';

class VocabularyListPage extends StatefulWidget {
  final String title;
  
  const VocabularyListPage({
    super.key, 
    this.title = 'Kho từ vựng thông minh',
  });

  @override
  State<VocabularyListPage> createState() => _VocabularyListPageState();
}

class _VocabularyListPageState extends State<VocabularyListPage> {
  String _selectedLevel = 'B1';
  
  // Dữ liệu mẫu phân theo trình độ và tiến trình
  final List<Map<String, dynamic>> allVocab = [
    {'word': 'Beginner', 'ipa': '/bɪˈɡɪnə(r)/', 'meaning': 'Người bắt đầu', 'level': 'A1', 'status': 'Mastered', 'example': 'This class is for total beginners.'},
    {'word': 'Persistent', 'ipa': '/pəˈsɪstənt/', 'meaning': 'Kiên trì, bền bỉ', 'level': 'B1', 'status': 'Learning', 'example': 'She is persistent in her efforts.'},
    {'word': 'Collaborate', 'ipa': '/kəˈlæbəreɪt/', 'meaning': 'Cộng tác, hợp tác', 'level': 'B1', 'status': 'New', 'example': 'Researchers are collaborating to develop a new vaccine.'},
    {'word': 'Substantial', 'ipa': '/səbˈstænʃl/', 'meaning': 'Đáng kể, quan trọng', 'level': 'B2', 'status': 'New', 'example': 'A substantial amount of money.'},
    {'word': 'Pragmatic', 'ipa': '/præɡˈmætɪk/', 'meaning': 'Thực dụng, thực tế', 'level': 'C1', 'status': 'New', 'example': 'We need a pragmatic approach to this problem.'},
  ];

  @override
  Widget build(BuildContext context) {
    final filteredList = allVocab.where((v) => v['level'] == _selectedLevel).toList();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => context.pop(),
        ),
        title: Text(widget.title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
      body: Column(
        children: [
          _buildLevelSelector(),
          Expanded(
            child: Stack(
              children: [
                filteredList.isEmpty 
                  ? _buildEmptyState()
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(20, 10, 20, 100),
                      itemCount: filteredList.length,
                      itemBuilder: (context, index) {
                        final item = filteredList[index];
                        return FadeInUp(
                          delay: Duration(milliseconds: 100 * index),
                          child: _buildVocabCard(item),
                        );
                      },
                    ),
                _buildAICoachButton(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLevelSelector() {
    final levels = ['A1', 'A2', 'B1', 'B2', 'C1'];
    return Container(
      height: 50,
      margin: const EdgeInsets.symmetric(vertical: 10),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: levels.length,
        itemBuilder: (context, index) {
          final level = levels[index];
          final isSelected = _selectedLevel == level;
          return Padding(
            padding: const EdgeInsets.only(right: 10),
            child: ChoiceChip(
              label: Text(level),
              selected: isSelected,
              onSelected: (selected) {
                if (selected) setState(() => _selectedLevel = level);
              },
              selectedColor: AppColors.primary,
              backgroundColor: AppColors.surface,
              labelStyle: TextStyle(
                color: isSelected ? Colors.white : Colors.white54,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.lock_outline_rounded, size: 64, color: Colors.white10),
          const SizedBox(height: 16),
          Text(
            'Cấp độ $_selectedLevel chưa được mở khóa',
            style: TextStyle(color: Colors.white38, fontSize: 16),
          ),
          const SizedBox(height: 8),
          const Text(
            'Hãy tiếp tục học để bổ sung từ vựng mới!',
            style: TextStyle(color: Colors.white24, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildAICoachButton() {
    return Positioned(
      bottom: 20,
      left: 20,
      right: 20,
      child: FadeInUp(
        child: ElevatedButton(
          onPressed: () => context.push('/chat'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 18),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            elevation: 8,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.psychology_rounded),
              const SizedBox(width: 12),
              Text('Luyện tập từ vựng trình độ $_selectedLevel', style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildVocabCard(Map<String, dynamic> item) {
    Color statusColor;
    String statusText;
    switch (item['status']) {
      case 'Mastered':
        statusColor = Colors.green;
        statusText = 'Đã thuộc';
        break;
      case 'Learning':
        statusColor = Colors.orange;
        statusText = 'Đang học';
        break;
      default:
        statusColor = AppColors.primary;
        statusText = 'Từ mới';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(item['word']!, style: const TextStyle(color: AppColors.primary, fontSize: 22, fontWeight: FontWeight.bold)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(color: statusColor.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
                child: Text(statusText, style: TextStyle(color: statusColor, fontSize: 10, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(item['ipa']!, style: const TextStyle(color: Colors.white54, fontSize: 14, fontStyle: FontStyle.italic)),
          const SizedBox(height: 12),
          Text(item['meaning']!, style: const TextStyle(color: AppColors.textPrimary, fontSize: 16, fontWeight: FontWeight.w500)),
          const SizedBox(height: 12),
          _buildExampleBox(item['example']!),
        ],
      ),
    );
  }

  Widget _buildExampleBox(String example) {
    return Container(
      padding: const EdgeInsets.all(12),
      width: double.infinity,
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.03), borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Ví dụ:', style: TextStyle(color: Colors.white38, fontSize: 12)),
          const SizedBox(height: 4),
          Text(example, style: const TextStyle(color: AppColors.textSecondary, fontSize: 14, height: 1.4)),
        ],
      ),
    );
  }
}
