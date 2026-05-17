import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppSettings {
  final bool isDarkMode;
  final bool isNotificationEnabled;
  final double aiSpeed;
  final String targetLevel;
  
  // New notification fields
  final int reminderHour;
  final int reminderMinute;
  final bool isProgressReportEnabled;
  final bool isAiTipEnabled;
  final bool isStreakWarningEnabled;

  AppSettings({
    this.isDarkMode = true,
    this.isNotificationEnabled = true,
    this.aiSpeed = 1.0,
    this.targetLevel = 'B1',
    this.reminderHour = 20,
    this.reminderMinute = 0,
    this.isProgressReportEnabled = true,
    this.isAiTipEnabled = false,
    this.isStreakWarningEnabled = true,
  });

  AppSettings copyWith({
    bool? isDarkMode,
    bool? isNotificationEnabled,
    double? aiSpeed,
    String? targetLevel,
    int? reminderHour,
    int? reminderMinute,
    bool? isProgressReportEnabled,
    bool? isAiTipEnabled,
    bool? isStreakWarningEnabled,
  }) {
    return AppSettings(
      isDarkMode: isDarkMode ?? this.isDarkMode,
      isNotificationEnabled: isNotificationEnabled ?? this.isNotificationEnabled,
      aiSpeed: aiSpeed ?? this.aiSpeed,
      targetLevel: targetLevel ?? this.targetLevel,
      reminderHour: reminderHour ?? this.reminderHour,
      reminderMinute: reminderMinute ?? this.reminderMinute,
      isProgressReportEnabled: isProgressReportEnabled ?? this.isProgressReportEnabled,
      isAiTipEnabled: isAiTipEnabled ?? this.isAiTipEnabled,
      isStreakWarningEnabled: isStreakWarningEnabled ?? this.isStreakWarningEnabled,
    );
  }
}

class SettingsNotifier extends StateNotifier<AppSettings> {
  SettingsNotifier() : super(AppSettings()) {
    _loadSettings();
  }

  static const String _keyDarkMode = 'dark_mode';
  static const String _keyNotifications = 'notifications';
  static const String _keyAiSpeed = 'ai_speed';
  static const String _keyTargetLevel = 'target_level';
  static const String _keyReminderHour = 'reminder_hour';
  static const String _keyReminderMinute = 'reminder_minute';
  static const String _keyProgressReport = 'progress_report';
  static const String _keyAiTip = 'ai_tip';
  static const String _keyStreakWarning = 'streak_warning';

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    state = AppSettings(
      isDarkMode: prefs.getBool(_keyDarkMode) ?? true,
      isNotificationEnabled: prefs.getBool(_keyNotifications) ?? true,
      aiSpeed: prefs.getDouble(_keyAiSpeed) ?? 1.0,
      targetLevel: prefs.getString(_keyTargetLevel) ?? 'B1',
      reminderHour: prefs.getInt(_keyReminderHour) ?? 20,
      reminderMinute: prefs.getInt(_keyReminderMinute) ?? 0,
      isProgressReportEnabled: prefs.getBool(_keyProgressReport) ?? true,
      isAiTipEnabled: prefs.getBool(_keyAiTip) ?? false,
      isStreakWarningEnabled: prefs.getBool(_keyStreakWarning) ?? true,
    );
  }

  Future<void> toggleDarkMode(bool value) async {
    state = state.copyWith(isDarkMode: value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyDarkMode, value);
  }

  Future<void> toggleNotifications(bool value) async {
    state = state.copyWith(isNotificationEnabled: value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyNotifications, value);
  }

  Future<void> setAiSpeed(double value) async {
    state = state.copyWith(aiSpeed: value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_keyAiSpeed, value);
  }

  Future<void> setTargetLevel(String value) async {
    state = state.copyWith(targetLevel: value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyTargetLevel, value);
  }

  Future<void> setReminderTime(int hour, int minute) async {
    state = state.copyWith(reminderHour: hour, reminderMinute: minute);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_keyReminderHour, hour);
    await prefs.setInt(_keyReminderMinute, minute);
  }

  Future<void> toggleProgressReport(bool value) async {
    state = state.copyWith(isProgressReportEnabled: value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyProgressReport, value);
  }

  Future<void> toggleAiTip(bool value) async {
    state = state.copyWith(isAiTipEnabled: value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyAiTip, value);
  }

  Future<void> toggleStreakWarning(bool value) async {
    state = state.copyWith(isStreakWarningEnabled: value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyStreakWarning, value);
  }
}

final settingsProvider = StateNotifierProvider<SettingsNotifier, AppSettings>((ref) {
  return SettingsNotifier();
});
