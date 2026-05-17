import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ai_english_coach/features/gamification/providers/gamification_provider.dart';

class LeaderboardScreen extends ConsumerWidget {
  const LeaderboardScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final leaderboardAsync = ref.watch(leaderboardProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Leaderboard'),
        centerTitle: true,
        elevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.black,
      ),
      body: leaderboardAsync.when(
        data: (entries) => ListView.builder(
          itemCount: entries.length,
          itemBuilder: (context, index) {
            final entry = entries[index];
            final isTopThree = index < 3;
            
            return Card(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: isTopThree ? Colors.amber : Colors.blueGrey[100],
                  child: Text(
                    '${index + 1}',
                    style: TextStyle(
                      color: isTopThree ? Colors.white : Colors.blueGrey,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                title: Text(
                  entry.fullName ?? 'User ${entry.userId}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                subtitle: Text('Level ${entry.level}'),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '${entry.totalXp} XP',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.blueAccent,
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('Error: $err')),
      ),
    );
  }
}
