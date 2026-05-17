import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:ai_english_coach/features/auth/presentation/providers/auth_provider.dart';

class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final user = authState.user;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Cá nhân'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => context.go('/'),
        ),
      ),
      body: Column(
        children: [
          const SizedBox(height: 40),
          CircleAvatar(
            radius: 50,
            backgroundColor: AppColors.primary.withOpacity(0.1),
            child: const Icon(Icons.person_rounded, size: 50, color: AppColors.primary),
          ),
          const SizedBox(height: 16),
          Text(
            user?.fullName ?? 'Học viên',
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          Text(
            user?.email ?? '',
            style: const TextStyle(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 40),
          _buildProfileItem(Icons.settings, 'Cài đặt', () {
            context.push('/settings');
          }),
          _buildProfileItem(Icons.notifications, 'Thông báo', () {
            context.push('/notifications');
          }),
          _buildProfileItem(Icons.help_outline, 'Trung tâm trợ giúp', () {
            context.push('/support');
          }),
          _buildProfileItem(
            Icons.logout, 
            'Đăng xuất', 
            () {
              ref.read(authProvider.notifier).logout();
              context.go('/login');
            }, 
            isDestructive: true
          ),
        ],
      ),
    );
  }

  Widget _buildProfileItem(IconData icon, String title, VoidCallback onTap, {bool isDestructive = false}) {
    return ListTile(
      leading: Icon(icon, color: isDestructive ? Colors.redAccent : AppColors.textPrimary),
      title: Text(title, style: TextStyle(color: isDestructive ? Colors.redAccent : AppColors.textPrimary)),
      trailing: const Icon(Icons.chevron_right, size: 20),
      onTap: onTap,
    );
  }
}
