import 'dart:html' as html; // Cho môi trường Web
import 'package:flutter/material.dart';
import 'package:ai_english_coach/theme/app_colors.dart';

class SupportCenterPage extends StatefulWidget {
  const SupportCenterPage({super.key});

  @override
  State<SupportCenterPage> createState() => _SupportCenterPageState();
}

class _SupportCenterPageState extends State<SupportCenterPage> {
  final TextEditingController _searchController = TextEditingController();
  
  final List<Map<String, String>> _allFaqs = [
    {
      'question': 'Cách kết nối micro để luyện nói?',
      'answer': 'Bạn cần cấp quyền truy cập micro cho ứng dụng trong phần cài đặt điện thoại. Sau khi cấp quyền, hãy nhấn vào biểu tượng mic ở trang Chat để bắt đầu nói.',
    },
    {
      'question': 'Làm sao để đổi trình độ học tập?',
      'answer': 'Bạn hãy vào tab Cá nhân -> Cài đặt -> Trình độ mục tiêu để thay đổi độ khó của các bài học.',
    },
    {
      'question': 'Dữ liệu của tôi có được bảo mật không?',
      'answer': 'Chúng tôi cam kết bảo mật 100% dữ liệu của học viên. Bạn có thể xem chi tiết tại phần Chính sách bảo mật.',
    },
    {
      'question': 'Làm sao để khôi phục Streak đã mất?',
      'answer': 'Streak thể hiện sự chuyên cần của bạn. Hiện tại hệ thống không hỗ trợ khôi phục Streak để khuyến khích thói quen học tập đều đặn mỗi ngày.',
    },
  ];

  List<Map<String, String>> _filteredFaqs = [];

  @override
  void initState() {
    super.initState();
    _filteredFaqs = _allFaqs;
  }

  void _filterFaqs(String query) {
    setState(() {
      _filteredFaqs = _allFaqs
          .where((faq) => 
              faq['question']!.toLowerCase().contains(query.toLowerCase()) ||
              faq['answer']!.toLowerCase().contains(query.toLowerCase()))
          .toList();
    });
  }

  void _launchZalo() {
    // Giả sử link Zalo hỗ trợ
    html.window.open('https://zalo.me/0123456789', '_blank');
  }

  void _launchEmail() {
    final Uri emailLaunchUri = Uri(
      scheme: 'mailto',
      path: 'support@aienglishcoach.com',
      queryParameters: {'subject': 'Hỗ trợ học viên AI Coach'},
    );
    html.window.open(emailLaunchUri.toString(), '_blank');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Trung tâm trợ giúp'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _buildSearchBar(),
          const SizedBox(height: 30),
          _buildSectionHeader('Liên hệ hỗ trợ'),
          _buildContactButtons(),
          const SizedBox(height: 30),
          _buildSectionHeader('Câu hỏi thường gặp'),
          if (_filteredFaqs.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: Text('Không tìm thấy câu trả lời phù hợp', style: TextStyle(color: Colors.white24)),
              ),
            )
          else
            ..._filteredFaqs.map((faq) => _buildFAQItem(faq['question']!, faq['answer']!)).toList(),
        ],
      ),
    );
  }

  Widget _buildSearchBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: TextField(
        controller: _searchController,
        onChanged: _filterFaqs,
        style: const TextStyle(color: Colors.white),
        decoration: const InputDecoration(
          icon: Icon(Icons.search, color: AppColors.textSecondary),
          hintText: 'Tìm kiếm câu trả lời...',
          border: InputBorder.none,
          hintStyle: TextStyle(color: AppColors.textSecondary),
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12, left: 4),
      child: Text(
        title.toUpperCase(),
        style: const TextStyle(color: Colors.white38, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.2),
      ),
    );
  }

  Widget _buildContactButtons() {
    return Row(
      children: [
        Expanded(
          child: _buildContactCard(
            'Hỗ trợ Zalo',
            Icons.chat_bubble_outline_rounded,
            Colors.blue,
            _launchZalo,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildContactCard(
            'Gửi Email',
            Icons.email_outlined,
            Colors.orange,
            _launchEmail,
          ),
        ),
      ],
    );
  }

  Widget _buildContactCard(String title, IconData icon, Color color, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withOpacity(0.2)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 30),
            const SizedBox(height: 8),
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
          ],
        ),
      ),
    );
  }

  Widget _buildFAQItem(String question, String answer) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: ExpansionTile(
        title: Text(question, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
        childrenPadding: const EdgeInsets.only(left: 16, right: 16, bottom: 16),
        expandedAlignment: Alignment.topLeft,
        children: [
          Text(
            answer,
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 14, height: 1.5),
          ),
        ],
      ),
    );
  }
}
