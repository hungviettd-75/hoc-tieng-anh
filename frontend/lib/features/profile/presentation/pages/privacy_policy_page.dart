import 'package:flutter/material.dart';
import 'package:ai_english_coach/theme/app_colors.dart';

class PrivacyPolicyPage extends StatelessWidget {
  const PrivacyPolicyPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Chính sách bảo mật'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSection('1. Thu thập thông tin', 
              'Chúng tôi thu thập thông tin cơ bản như Email và Họ tên để quản lý tài khoản của bạn. Dữ liệu giọng nói được sử dụng duy nhất cho mục đích phân tích lỗi phát âm và cải thiện phản hồi từ AI.'),
            _buildSection('2. Sử dụng dữ liệu', 
              'Dữ liệu của bạn giúp chúng tôi cá nhân hóa lộ trình học tập. Chúng tôi cam kết không chia sẻ dữ liệu cá nhân của bạn cho bên thứ ba vì mục đích quảng cáo.'),
            _buildSection('3. Bảo mật', 
              'Tất cả dữ liệu được truyền tải qua giao thức HTTPS mã hóa và được lưu trữ trên các máy chủ bảo mật của Google Cloud.'),
            _buildSection('4. Quyền của bạn', 
              'Bạn có quyền yêu cầu truy xuất hoặc xóa vĩnh viễn dữ liệu cá nhân của mình bất kỳ lúc nào thông qua phần hỗ trợ trong ứng dụng.'),
            const SizedBox(height: 40),
            const Center(
              child: Text('Cập nhật lần cuối: 16/05/2026', 
                style: TextStyle(color: Colors.white24, fontSize: 12)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSection(String title, String content) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.primary)),
          const SizedBox(height: 8),
          Text(content, style: const TextStyle(color: AppColors.textSecondary, height: 1.6, fontSize: 14)),
        ],
      ),
    );
  }
}
