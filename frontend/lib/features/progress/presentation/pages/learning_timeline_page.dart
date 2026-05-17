import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/memory_provider.dart';
import '../../models/memory_insight_model.dart';

class LearningTimelinePage extends ConsumerWidget {
  final int userId;

  const LearningTimelinePage({super.key, required this.userId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final memoryAsync = ref.watch(memoryInsightsProvider(userId));

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // Dark Navy
      appBar: AppBar(
        title: const Text('AI Learning Journey', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: memoryAsync.when(
        data: (data) => _buildTimeline(context, data),
        loading: () => const Center(child: CircularProgressIndicator(color: Colors.cyanAccent)),
        error: (err, stack) => Center(child: Text('Error: $err', style: const TextStyle(color: Colors.red))),
      ),
    );
  }

  Widget _buildTimeline(BuildContext context, MemoryInsight data) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildAIThoughtBubble(data.aiInsights),
          const SizedBox(height: 30),
          const Text(
            'Your Milestones',
            style: TextStyle(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 20),
          ...data.timeline.map((event) => _buildTimelineItem(event)).toList(),
        ],
      ),
    );
  }

  Widget _buildAIThoughtBubble(List<String> insights) {
    if (insights.isEmpty) return const SizedBox.shrink();
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1E293B), Color(0xFF334155)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.cyanAccent.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.cyanAccent.withOpacity(0.1),
            blurRadius: 20,
            spreadRadius: 5,
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.psychology, color: Colors.cyanAccent),
              const SizedBox(width: 10),
              Text(
                'AI Memory Insights',
                style: TextStyle(
                  color: Colors.cyanAccent.withOpacity(0.9),
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
            ],
          ),
          const SizedBox(height: 15),
          Text(
            insights.first, // Show the most relevant one
            style: const TextStyle(color: Colors.white70, fontSize: 15, fontStyle: FontStyle.italic),
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineItem(TimelineEvent event) {
    Color itemColor;
    IconData icon;

    switch (event.type) {
      case 'goal':
        itemColor = Colors.orangeAccent;
        icon = Icons.flag;
        break;
      case 'achievement':
        itemColor = Colors.greenAccent;
        icon = Icons.emoji_events;
        break;
      default:
        itemColor = Colors.blueAccent;
        icon = Icons.bolt;
    }

    return IntrinsicHeight(
      child: Row(
        children: [
          Column(
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: itemColor,
                  shape: BoxShape.circle,
                  boxShadow: [BoxShadow(color: itemColor.withOpacity(0.5), blurRadius: 10)],
                ),
              ),
              Expanded(
                child: Container(
                  width: 2,
                  color: Colors.white10,
                ),
              ),
            ],
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 30),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    event.date,
                    style: const TextStyle(color: Colors.white38, fontSize: 12),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    event.event,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
          Icon(icon, color: itemColor.withOpacity(0.5), size: 24),
        ],
      ),
    );
  }
}
