import 'dart:math';
import 'package:flutter/material.dart';
import 'package:ai_english_coach/theme/app_colors.dart';

/// Custom painter cho waveform animation khi đang ghi âm.
/// Hiển thị các bars phản ứng theo audio amplitude.
class WaveformPainter extends CustomPainter {
  final List<double> amplitudes;
  final Color color;
  final Color secondaryColor;
  final double animationValue;

  WaveformPainter({
    required this.amplitudes,
    this.color = AppColors.primary,
    this.secondaryColor = AppColors.secondary,
    this.animationValue = 0.0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (amplitudes.isEmpty) {
      _drawIdleWaveform(canvas, size);
      return;
    }

    final barCount = min(amplitudes.length, 60);
    final barWidth = size.width / (barCount * 2);
    final maxHeight = size.height * 0.8;

    for (int i = 0; i < barCount; i++) {
      final ampIndex = amplitudes.length - barCount + i;
      if (ampIndex < 0) continue;

      final amplitude = amplitudes[ampIndex].clamp(0.05, 1.0);
      final barHeight = amplitude * maxHeight;

      final x = i * barWidth * 2 + barWidth / 2;
      final y = (size.height - barHeight) / 2;

      // Gradient per bar
      final progress = i / barCount;
      final barColor = Color.lerp(color, secondaryColor, progress)!;

      final paint = Paint()
        ..color = barColor.withOpacity(0.8)
        ..style = PaintingStyle.fill;

      final rrect = RRect.fromRectAndRadius(
        Rect.fromLTWH(x, y, barWidth, barHeight),
        Radius.circular(barWidth / 2),
      );
      canvas.drawRRect(rrect, paint);
    }
  }

  void _drawIdleWaveform(Canvas canvas, Size size) {
    // Vẽ idle waveform nhẹ nhàng
    final barCount = 30;
    final barWidth = size.width / (barCount * 2);
    final maxHeight = size.height * 0.3;

    for (int i = 0; i < barCount; i++) {
      final phase = (i / barCount) * 2 * pi + animationValue * 2 * pi;
      final amplitude = (sin(phase) * 0.5 + 0.5) * 0.4 + 0.1;
      final barHeight = amplitude * maxHeight;

      final x = i * barWidth * 2 + barWidth / 2;
      final y = (size.height - barHeight) / 2;

      final progress = i / barCount;
      final barColor = Color.lerp(color, secondaryColor, progress)!;

      final paint = Paint()
        ..color = barColor.withOpacity(0.3)
        ..style = PaintingStyle.fill;

      final rrect = RRect.fromRectAndRadius(
        Rect.fromLTWH(x, y, barWidth, barHeight),
        Radius.circular(barWidth / 2),
      );
      canvas.drawRRect(rrect, paint);
    }
  }

  @override
  bool shouldRepaint(covariant WaveformPainter oldDelegate) {
    return oldDelegate.amplitudes != amplitudes ||
        oldDelegate.animationValue != animationValue;
  }
}

/// Widget hiển thị waveform với animation
class WaveformWidget extends StatefulWidget {
  final List<double> amplitudes;
  final bool isRecording;
  final double height;

  const WaveformWidget({
    super.key,
    required this.amplitudes,
    this.isRecording = false,
    this.height = 120,
  });

  @override
  State<WaveformWidget> createState() => _WaveformWidgetState();
}

class _WaveformWidgetState extends State<WaveformWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          height: widget.height,
          decoration: BoxDecoration(
            color: AppColors.surface.withOpacity(0.5),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: widget.isRecording
                  ? AppColors.primary.withOpacity(0.3)
                  : Colors.white10,
            ),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: CustomPaint(
              size: Size(double.infinity, widget.height),
              painter: WaveformPainter(
                amplitudes: widget.amplitudes,
                animationValue: _controller.value,
              ),
            ),
          ),
        );
      },
    );
  }
}
