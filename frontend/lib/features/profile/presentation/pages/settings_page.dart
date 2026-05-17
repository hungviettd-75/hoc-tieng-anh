import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:ai_english_coach/features/auth/presentation/providers/auth_provider.dart';

import 'package:ai_english_coach/features/profile/presentation/providers/settings_provider.dart';
import 'package:ai_english_coach/features/profile/presentation/pages/privacy_policy_page.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);
    final settingsNotifier = ref.read(settingsProvider.notifier);
    final authState = ref.watch(authProvider);
    final user = authState.user;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Cài đặt hệ thống'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => context.pop(),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _buildSectionHeader('Tài khoản'),
          _buildSettingTile(
            Icons.person_outline_rounded,
            'Tên hiển thị',
            subtitle: user?.fullName ?? 'Học viên',
            onTap: () {},
          ),
          _buildSettingTile(
            Icons.email_outlined,
            'Email',
            subtitle: user?.email ?? '',
            onTap: () {},
          ),
          
          const SizedBox(height: 30),
          _buildSectionHeader('Cấu hình AI Coach'),
          _buildLevelPicker(settings.targetLevel, settingsNotifier),
          const SizedBox(height: 16),
          _buildSpeedSlider(settings.aiSpeed, settingsNotifier),
          
          const SizedBox(height: 30),
          _buildSectionHeader('Thông báo & Hiển thị'),
          SwitchListTile(
            secondary: const Icon(Icons.notifications_active_outlined, color: AppColors.primary),
            title: const Text('Nhắc nhở học tập hàng ngày'),
            value: settings.isNotificationEnabled,
            onChanged: (val) => settingsNotifier.toggleNotifications(val),
            activeColor: AppColors.primary,
          ),
          SwitchListTile(
            secondary: const Icon(Icons.dark_mode_outlined, color: AppColors.primary),
            title: const Text('Chế độ tối (Dark Mode)'),
            value: settings.isDarkMode,
            onChanged: (val) => settingsNotifier.toggleDarkMode(val),
            activeColor: AppColors.primary,
          ),
          
          const SizedBox(height: 40),
          _buildSectionHeader('Khác'),
          _buildSettingTile(Icons.info_outline_rounded, 'Về ứng dụng', onTap: () {
            showAboutDialog(
              context: context,
              applicationName: 'AI English Coach',
              applicationVersion: '1.0.0+1',
              applicationIcon: const Icon(Icons.psychology_rounded, size: 50, color: AppColors.primary),
              children: [
                const Text('Ứng dụng học tiếng Anh tương tác với trí tuệ nhân tạo thế hệ mới. Giúp bạn làm chủ giao tiếp một cách tự tin nhất.'),
              ],
            );
          }),
          _buildSettingTile(Icons.policy_outlined, 'Chính sách bảo mật', onTap: () {
            Navigator.push(context, MaterialPageRoute(builder: (_) => const PrivacyPolicyPage()));
          }),
        ],
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

  Widget _buildSettingTile(IconData icon, String title, {String? subtitle, required VoidCallback onTap}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: ListTile(
        leading: Icon(icon, color: AppColors.primary, size: 22),
        title: Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
        subtitle: subtitle != null ? Text(subtitle, style: const TextStyle(color: Colors.white38, fontSize: 13)) : null,
        trailing: const Icon(Icons.chevron_right_rounded, color: Colors.white24),
        onTap: onTap,
      ),
    );
  }

  Widget _buildLevelPicker(String currentLevel, SettingsNotifier notifier) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Trình độ mục tiêu', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: ['A1', 'A2', 'B1', 'B2', 'C1'].map((level) {
              final isSelected = currentLevel == level;
              return GestureDetector(
                onTap: () => notifier.setTargetLevel(level),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: isSelected ? AppColors.primary : Colors.white.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    level,
                    style: TextStyle(
                      color: isSelected ? Colors.white : Colors.white54,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildSpeedSlider(double currentSpeed, SettingsNotifier notifier) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Tốc độ nói của AI', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
              Text('${currentSpeed.toStringAsFixed(1)}x', style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold)),
            ],
          ),
          Slider(
            value: currentSpeed,
            min: 0.5,
            max: 2.0,
            divisions: 6,
            activeColor: AppColors.primary,
            inactiveColor: Colors.white10,
            onChanged: (val) => notifier.setAiSpeed(val),
          ),
          const Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Chậm', style: TextStyle(color: Colors.white38, fontSize: 12)),
              Text('Nhanh', style: TextStyle(color: Colors.white38, fontSize: 12)),
            ],
          ),
        ],
      ),
    );
  }
}
