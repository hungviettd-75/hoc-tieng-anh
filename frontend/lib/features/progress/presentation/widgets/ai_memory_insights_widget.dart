import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/memory_provider.dart';
import '../pages/learning_timeline_page.dart';

class AIMemoryInsightsWidget extends ConsumerWidget {
  final int userId;

  const AIMemoryInsightsWidget({super.key, required this.userId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final memoryAsync = ref.watch(memoryInsightsProvider(userId));

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.cyanAccent.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.auto_awesome, color: Colors.cyanAccent, size: 20),
                  SizedBox(width: 8),
                  Text(
                    'AI Memory Insights',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              IconButton(
                icon: const Icon(Icons.arrow_forward_ios, color: Colors.white38, size: 16),
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => LearningTimelinePage(userId: userId),
                    ),
                  );
                },
              ),
            ],
          ),
          const SizedBox(height: 15),
          memoryAsync.when(
            data: (data) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (data.aiInsights.isNotEmpty)
                  Text(
                    data.aiInsights.first,
                    style: const TextStyle(color: Colors.white70, fontSize: 14),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  )
                else
                  const Text(
                    'AI is getting to know you. Keep practicing to build memories!',
                    style: TextStyle(color: Colors.white38, fontSize: 14),
                  ),
                const SizedBox(height: 15),
                _buildMiniTimeline(data.timeline),
              ],
            ),
            loading: () => const Center(child: LinearProgressIndicator(color: Colors.cyanAccent)),
            error: (err, stack) => Text('Error loading insights: $err', style: const TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  Widget _buildMiniTimeline(List<dynamic> timeline) {
    if (timeline.isEmpty) return const SizedBox.shrink();
    
    return Row(
      children: timeline.take(3).map((event) {
        return Expanded(
          child: Container(
            margin: const EdgeInsets.only(right: 8),
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.05),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              event.event,
              style: const TextStyle(color: Colors.white60, fontSize: 11),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        );
      }).toList(),
    );
  }
}
