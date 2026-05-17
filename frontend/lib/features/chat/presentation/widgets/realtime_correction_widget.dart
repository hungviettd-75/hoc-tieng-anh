import 'package:flutter/material.dart';
import 'package:animate_do/animate_do.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../providers/realtime_chat_provider.dart';

class RealtimeCorrectionWidget extends StatelessWidget {
  final List<RealtimeCorrection> corrections;
  final String formattedText;
  
  const RealtimeCorrectionWidget({
    super.key,
    required this.corrections,
    required this.formattedText,
  });

  @override
  Widget build(BuildContext context) {
    if (corrections.isEmpty) return const SizedBox.shrink();

    return FadeInDown(
      duration: const Duration(milliseconds: 300),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.amberAccent,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black26,
              blurRadius: 20,
              spreadRadius: 2,
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                const Icon(Icons.lightbulb_outline, color: Colors.black, size: 20),
                const SizedBox(width: 8),
                Text(
                  "AI Correction",
                  style: const TextStyle(
                    color: Colors.black,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              formattedText,
              style: const TextStyle(
                color: Colors.black,
                fontSize: 15,
                height: 1.5,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
