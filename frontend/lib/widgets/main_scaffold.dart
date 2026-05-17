import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';

class MainScaffold extends StatelessWidget {
  final Widget child;
  const MainScaffold({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.toString();
    
    int getCurrentIndex() {
      if (location == '/') return 0;
      if (location == '/speaking') return 1;
      if (location == '/learn') return 2;
      if (location == '/progress') return 3;
      if (location == '/profile') return 4;
      return 0;
    }

    return Scaffold(
      body: child,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          border: Border(top: BorderSide(color: AppColors.surface, width: 1)),
        ),
        child: BottomNavigationBar(
          currentIndex: getCurrentIndex(),
          onTap: (index) {
            switch (index) {
              case 0: context.go('/'); break;
              case 1: context.go('/speaking'); break;
              case 2: context.go('/learn'); break;
              case 3: context.go('/progress'); break;
              case 4: context.go('/profile'); break;
            }
          },
          items: const [
            BottomNavigationBarItem(icon: Icon(Icons.home_filled), label: 'Trang chủ'),
            BottomNavigationBarItem(icon: Icon(Icons.mic_rounded), label: 'Phát âm'),
            BottomNavigationBarItem(icon: Icon(Icons.school_rounded), label: 'Học tập'),
            BottomNavigationBarItem(icon: Icon(Icons.bar_chart_rounded), label: 'Tiến độ'),
            BottomNavigationBarItem(icon: Icon(Icons.person_rounded), label: 'Cá nhân'),
          ],
        ),
      ),
    );
  }
}
