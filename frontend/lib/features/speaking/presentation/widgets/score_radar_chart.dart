import 'dart:math';
import 'package:flutter/material.dart';
import 'package:ai_english_coach/theme/app_colors.dart';

/// Radar chart hiển thị 4 metrics: Fluency, Pronunciation, Confidence, Intonation.
/// Sử dụng CustomPainter thay vì fl_chart radar (vì fl_chart chưa hỗ trợ radar tốt).
class ScoreRadarChart extends StatefulWidget {
  final double fluency;
  final double pronunciation;
  final double confidence;
  final double intonation;
  final double size;

  const ScoreRadarChart({
    super.key,
    required this.fluency,
    required this.pronunciation,
    required this.confidence,
    required this.intonation,
    this.size = 200,
  });

  @override
  State<ScoreRadarChart> createState() => _ScoreRadarChartState();
}

class _ScoreRadarChartState extends State<ScoreRadarChart>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _animation = CurvedAnimation(parent: _controller, curve: Curves.easeOutBack);
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return SizedBox(
          width: widget.size,
          height: widget.size,
          child: CustomPaint(
            painter: _RadarChartPainter(
              scores: [
                widget.fluency * _animation.value,
                widget.pronunciation * _animation.value,
                widget.confidence * _animation.value,
                widget.intonation * _animation.value,
              ],
              labels: ['Trôi chảy', 'Phát âm', 'Tự tin', 'Ngữ điệu'],
            ),
          ),
        );
      },
    );
  }
}

class _RadarChartPainter extends CustomPainter {
  final List<double> scores;
  final List<String> labels;

  _RadarChartPainter({required this.scores, required this.labels});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = min(size.width, size.height) / 2.5;
    final sides = scores.length;

    // Vẽ grid circles
    for (int i = 1; i <= 4; i++) {
      final gridRadius = radius * (i / 4);
      final gridPaint = Paint()
        ..color = Colors.white.withOpacity(0.08)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1;
      canvas.drawCircle(center, gridRadius, gridPaint);
    }

    // Vẽ grid lines (axes)
    for (int i = 0; i < sides; i++) {
      final angle = (2 * pi * i / sides) - pi / 2;
      final endX = center.dx + radius * cos(angle);
      final endY = center.dy + radius * sin(angle);

      final axisPaint = Paint()
        ..color = Colors.white.withOpacity(0.1)
        ..strokeWidth = 1;
      canvas.drawLine(center, Offset(endX, endY), axisPaint);
    }

    // Vẽ data polygon
    final path = Path();
    final gradientPoints = <Offset>[];

    for (int i = 0; i < sides; i++) {
      final angle = (2 * pi * i / sides) - pi / 2;
      final value = (scores[i] / 100).clamp(0.0, 1.0);
      final x = center.dx + radius * value * cos(angle);
      final y = center.dy + radius * value * sin(angle);
      gradientPoints.add(Offset(x, y));

      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    path.close();

    // Fill với gradient
    final fillPaint = Paint()
      ..shader = LinearGradient(
        colors: [
          AppColors.primary.withOpacity(0.3),
          AppColors.secondary.withOpacity(0.3),
        ],
      ).createShader(Rect.fromCenter(center: center, width: radius * 2, height: radius * 2))
      ..style = PaintingStyle.fill;
    canvas.drawPath(path, fillPaint);

    // Stroke
    final strokePaint = Paint()
      ..shader = const LinearGradient(
        colors: [AppColors.primary, AppColors.secondary],
      ).createShader(Rect.fromCenter(center: center, width: radius * 2, height: radius * 2))
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    canvas.drawPath(path, strokePaint);

    // Vẽ dots tại mỗi đỉnh
    for (final point in gradientPoints) {
      final dotPaint = Paint()
        ..color = AppColors.primary
        ..style = PaintingStyle.fill;
      canvas.drawCircle(point, 4, dotPaint);

      final dotGlow = Paint()
        ..color = AppColors.primary.withOpacity(0.3)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(point, 7, dotGlow);
    }

    // Vẽ labels
    for (int i = 0; i < sides; i++) {
      final angle = (2 * pi * i / sides) - pi / 2;
      final labelRadius = radius + 24;
      final x = center.dx + labelRadius * cos(angle);
      final y = center.dy + labelRadius * sin(angle);

      final textPainter = TextPainter(
        text: TextSpan(
          text: '${labels[i]}\n${scores[i].clamp(0, 100).toInt()}',
          style: TextStyle(
            color: AppColors.textSecondary,
            fontSize: 10,
            height: 1.3,
            fontWeight: FontWeight.w500,
          ),
        ),
        textDirection: TextDirection.ltr,
        textAlign: TextAlign.center,
      );
      textPainter.layout();
      textPainter.paint(
        canvas,
        Offset(x - textPainter.width / 2, y - textPainter.height / 2),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _RadarChartPainter oldDelegate) {
    return oldDelegate.scores != scores;
  }
}
