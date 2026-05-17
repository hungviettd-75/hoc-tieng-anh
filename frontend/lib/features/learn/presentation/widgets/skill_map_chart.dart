import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../../models/learning_models.dart';

class SkillMapChart extends StatelessWidget {
  final SkillLevel skillLevel;

  const SkillMapChart({super.key, required this.skillLevel});

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1.3,
      child: RadarChart(
        RadarChartData(
          radarTouchData: RadarTouchData(enabled: false),
          dataSets: [
            RadarDataSet(
              fillColor: AppColors.primary.withOpacity(0.4),
              borderColor: AppColors.primary,
              entryRadius: 4,
              dataEntries: [
                RadarEntry(value: skillLevel.vocabulary),
                RadarEntry(value: skillLevel.grammar),
                RadarEntry(value: skillLevel.pronunciation),
                RadarEntry(value: skillLevel.listening),
                RadarEntry(value: skillLevel.fluency),
              ],
              borderWidth: 2,
            ),
          ],
          radarBackgroundColor: Colors.transparent,
          borderData: FlBorderData(show: false),
          radarBorderData: const BorderSide(color: Colors.white24),

          tickCount: 5,
          ticksTextStyle: const TextStyle(color: Colors.transparent),
          tickBorderData: const BorderSide(color: Colors.white12),
          gridBorderData: const BorderSide(color: Colors.white24, width: 1.5),
          getTitle: (index, angle) {
            String text;
            switch (index) {
              case 0:
                text = 'Vocabulary';
                break;
              case 1:
                text = 'Grammar';
                break;
              case 2:
                text = 'Pronun.';
                break;
              case 3:
                text = 'Listening';
                break;
              case 4:
                text = 'Fluency';
                break;
              default:
                text = '';
            }
            return RadarChartTitle(
              text: text,
              angle: angle,
              positionPercentageOffset: 0.1,
            );
          },
          titleTextStyle: const TextStyle(color: Colors.white70, fontSize: 12),
        ),
        swapAnimationDuration: const Duration(milliseconds: 400),
      ),
    );
  }
}
