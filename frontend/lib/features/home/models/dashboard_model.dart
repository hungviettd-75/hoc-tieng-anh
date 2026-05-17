class DashboardStats {
  final String fullName;
  final String greeting;
  final String motivation;
  final XPStats xp;
  final StreakStats streak;
  final List<DailyGoal> dailyGoals;
  final List<String> recentActivity;

  DashboardStats({
    required this.fullName,
    required this.greeting,
    required this.motivation,
    required this.xp,
    required this.streak,
    required this.dailyGoals,
    required this.recentActivity,
  });

  factory DashboardStats.fromJson(Map<String, dynamic> json) {
    return DashboardStats(
      fullName: json['full_name'],
      greeting: json['greeting'],
      motivation: json['motivation'],
      xp: XPStats.fromJson(json['xp']),
      streak: StreakStats.fromJson(json['streak']),
      dailyGoals: (json['daily_goals'] as List).map((i) => DailyGoal.fromJson(i)).toList(),
      recentActivity: List<String>.from(json['recent_activity']),
    );
  }
}

class XPStats {
  final int totalXp;
  final int level;
  final int nextLevelXp;

  XPStats({required this.totalXp, required this.level, required this.nextLevelXp});

  factory XPStats.fromJson(Map<String, dynamic> json) {
    return XPStats(
      totalXp: json['total_xp'],
      level: json['level'],
      nextLevelXp: json['next_level_xp'],
    );
  }
}

class StreakStats {
  final int currentStreak;
  final int longestStreak;

  StreakStats({required this.currentStreak, required this.longestStreak});

  factory StreakStats.fromJson(Map<String, dynamic> json) {
    return StreakStats(
      currentStreak: json['current_streak'],
      longestStreak: json['longest_streak'],
    );
  }
}

class DailyGoal {
  final String goalType;
  final int targetValue;
  final int currentValue;

  DailyGoal({required this.goalType, required this.targetValue, required this.currentValue});

  factory DailyGoal.fromJson(Map<String, dynamic> json) {
    return DailyGoal(
      goalType: json['goal_type'],
      targetValue: json['target_value'],
      currentValue: json['current_value'],
    );
  }
}
