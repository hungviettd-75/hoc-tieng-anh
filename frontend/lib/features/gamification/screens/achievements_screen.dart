import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// import 'package:ai_english_coach/features/gamification/providers/gamification_provider.dart';

class AchievementsScreen extends ConsumerWidget {
  const AchievementsScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // In a real app, you would fetch achievements from a provider
    // For now, let's show a beautiful mock UI
    final List<Map<String, dynamic>> mockAchievements = [
      {'name': 'First Steps', 'description': 'Complete your first conversation', 'unlocked': true, 'icon': Icons.star},
      {'name': 'Chatterbox', 'description': 'Send 100 messages', 'unlocked': true, 'icon': Icons.message},
      {'name': 'Early Bird', 'description': 'Practice before 8 AM', 'unlocked': false, 'icon': Icons.wb_sunny},
      {'name': 'Polyglot', 'description': 'Reach Level 10', 'unlocked': false, 'icon': Icons.language},
      {'name': 'Streak Master', 'description': 'Maintain a 7-day streak', 'unlocked': false, 'icon': Icons.local_fire_department},
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Achievements'),
        centerTitle: true,
        elevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.black,
      ),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          childAspectRatio: 0.8,
        ),
        itemCount: mockAchievements.length,
        itemBuilder: (context, index) {
          final achievement = mockAchievements[index];
          final bool unlocked = achievement['unlocked'];

          return Container(
            decoration: BoxDecoration(
              color: unlocked ? Colors.white : Colors.grey[200],
              borderRadius: BorderRadius.circular(20),
              boxShadow: unlocked
                  ? [BoxShadow(color: Colors.blueAccent.withOpacity(0.1), blurRadius: 10, offset: const Offset(0, 5))]
                  : [],
              border: unlocked ? Border.all(color: Colors.blueAccent.withOpacity(0.3)) : null,
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  achievement['icon'],
                  size: 50,
                  color: unlocked ? Colors.blueAccent : Colors.grey[400],
                ),
                const SizedBox(height: 12),
                Text(
                  achievement['name'],
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: unlocked ? Colors.black87 : Colors.grey[600],
                  ),
                ),
                const SizedBox(height: 4),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8.0),
                  child: Text(
                    achievement['description'],
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 10,
                      color: unlocked ? Colors.grey[600] : Colors.grey[400],
                    ),
                  ),
                ),
                if (unlocked) ...[
                  const SizedBox(height: 8),
                  const Icon(Icons.check_circle, color: Colors.green, size: 20),
                ]
              ],
            ),
          );
        },
      ),
    );
  }
}
