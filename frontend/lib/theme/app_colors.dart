import 'package:flutter/material.dart';

class AppColors {
  // Dark Theme Palette
  static const Color background = Color(0xFF0F172A);
  static const Color surface = Color(0xFF1E293B);
  static const Color primary = Color(0xFF6366F1); // Indigo
  static const Color secondary = Color(0xFF8B5CF6); // Violet
  static const Color tertiary = Color(0xFFF59E0B); // Amber
  
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  
  static const Color success = Color(0xFF10B981);
  static const Color error = Color(0xFFEF4444);
  
  // Gradients
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, secondary],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
  
  static const LinearGradient surfaceGradient = LinearGradient(
    colors: [Color(0xFF1E293B), Color(0xFF0F172A)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );
}
