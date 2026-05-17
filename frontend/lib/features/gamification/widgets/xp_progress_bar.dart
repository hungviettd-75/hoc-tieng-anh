import 'package:flutter/material.dart';
import 'package:percent_indicator/linear_percent_indicator.dart';

class XpProgressBar extends StatelessWidget {
  final int currentXp;
  final int level;
  final double height;

  const XpProgressBar({
    Key? key,
    required this.currentXp,
    required this.level,
    this.height = 20.0,
  }) : super(key: key);

  @override
  Widget build(BuildContext method) {
    // Calculate progress based on level
    // Formula: Level = floor(sqrt(total_xp / 100)) + 1
    // So total_xp for level N: (N-1)^2 * 100
    // Total_xp for level N+1: N^2 * 100
    
    final int xpForCurrentLevel = ((level - 1) * (level - 1) * 100).toInt();
    final int xpForNextLevel = (level * level * 100).toInt();
    final int xpInCurrentLevel = currentXp - xpForCurrentLevel;
    final int xpRequiredForNextLevel = xpForNextLevel - xpForCurrentLevel;
    
    double percent = xpInCurrentLevel / xpRequiredForNextLevel;
    if (percent > 1.0) percent = 1.0;
    if (percent < 0.0) percent = 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Level $level',
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.blueAccent,
              ),
            ),
            Text(
              '$xpInCurrentLevel / $xpRequiredForNextLevel XP',
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 12,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        LinearPercentIndicator(
          lineHeight: height,
          percent: percent,
          center: Text(
            "${(percent * 100).toInt()}%",
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          barRadius: const Radius.circular(10),
          progressColor: Colors.blueAccent,
          backgroundColor: Colors.blueAccent.withOpacity(0.1),
          animation: true,
          animateFromLastPercent: true,
        ),
      ],
    );
  }
}
