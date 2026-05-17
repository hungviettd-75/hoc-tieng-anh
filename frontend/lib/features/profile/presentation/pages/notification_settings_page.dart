import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ai_english_coach/theme/app_colors.dart';

import 'package:ai_english_coach/features/profile/presentation/providers/settings_provider.dart';

class NotificationSettingsPage extends ConsumerWidget {
  const NotificationSettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);
    final notifier = ref.read(settingsProvider.notifier);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Cài đặt thông báo'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _buildSectionHeader('Lời nhắc học tập'),
          Container(
            decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16)),
            child: Column(
              children: [
                SwitchListTile(
                  title: const Text('Nhắc nhở hàng ngày'),
                  subtitle: const Text('Nhắc bạn vào học để duy trì thói quen'),
                  value: settings.isNotificationEnabled,
                  onChanged: (val) => notifier.toggleNotifications(val),
                  activeColor: AppColors.primary,
                ),
                if (settings.isNotificationEnabled) ...[
                  const Divider(color: Colors.white10, height: 1),
                  ListTile(
                    title: const Text('Thời gian nhắc'),
                    trailing: Text(
                      TimeOfDay(hour: settings.reminderHour, minute: settings.reminderMinute).format(context),
                      style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold),
                    ),
                    onTap: () async {
                      final time = await showTimePicker(
                        context: context, 
                        initialTime: TimeOfDay(hour: settings.reminderHour, minute: settings.reminderMinute),
                      );
                      if (time != null) notifier.setReminderTime(time.hour, time.minute);
                    },
                  ),
                ],
              ],
            ),
          ),
          
          const SizedBox(height: 30),
          _buildSectionHeader('Nội dung thông báo'),
          _buildNotificationSwitch(
            'Báo cáo tiến độ',
            'Nhận thông báo khi bạn lên cấp hoặc đạt thành tích',
            settings.isProgressReportEnabled,
            (val) => notifier.toggleProgressReport(val),
          ),
          _buildNotificationSwitch(
            'Mẹo từ AI Coach',
            'Các mẹo nhỏ giúp bạn học tiếng Anh hiệu quả hơn',
            settings.isAiTipEnabled,
            (val) => notifier.toggleAiTip(val),
          ),
          _buildNotificationSwitch(
            'Cảnh báo mất Streak',
            'Nhắc bạn khi sắp hết ngày mà chưa vào học',
            settings.isStreakWarningEnabled,
            (val) => notifier.toggleStreakWarning(val),
          ),
          
          const SizedBox(height: 40),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Text(
              'Lưu ý: Bạn có thể cần cấp quyền thông báo trong cài đặt hệ thống của điện thoại để các lời nhắc này hoạt động chính xác.',
              style: TextStyle(color: Colors.white.withOpacity(0.2), fontSize: 12),
              textAlign: TextAlign.center,
            ),
          ),
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

  Widget _buildNotificationSwitch(String title, String subtitle, bool value, Function(bool) onChanged) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16)),
      child: SwitchListTile(
        title: Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
        subtitle: Text(subtitle, style: const TextStyle(color: Colors.white38, fontSize: 12)),
        value: value,
        onChanged: onChanged,
        activeColor: AppColors.primary,
      ),
    );
  }
}
