class Achievement {
  final int id;
  final String name;
  final String? description;
  final String? iconUrl;
  final int requiredXp;
  final String? conditionType;
  final int? conditionValue;
  final DateTime createdAt;

  Achievement({
    required this.id,
    required this.name,
    this.description,
    this.iconUrl,
    this.requiredXp = 0,
    this.conditionType,
    this.conditionValue,
    required this.createdAt,
  });

  factory Achievement.fromJson(Map<String, dynamic> json) {
    return Achievement(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      iconUrl: json['icon_url'],
      requiredXp: json['required_xp'] ?? 0,
      conditionType: json['condition_type'],
      conditionValue: json['condition_value'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class UserAchievement {
  final int id;
  final int userId;
  final int achievementId;
  final DateTime unlockedAt;
  final Achievement achievement;

  UserAchievement({
    required this.id,
    required this.userId,
    required this.achievementId,
    required this.unlockedAt,
    required this.achievement,
  });

  factory UserAchievement.fromJson(Map<String, dynamic> json) {
    return UserAchievement(
      id: json['id'],
      userId: json['user_id'],
      achievementId: json['achievement_id'],
      unlockedAt: DateTime.parse(json['unlocked_at']),
      achievement: Achievement.fromJson(json['achievement']),
    );
  }
}

class Mission {
  final int id;
  final String title;
  final String? description;
  final int rewardXp;
  final String? missionType;
  final String? targetAction;
  final int? targetValue;
  final DateTime createdAt;

  Mission({
    required this.id,
    required this.title,
    this.description,
    this.rewardXp = 10,
    this.missionType,
    this.targetAction,
    this.targetValue,
    required this.createdAt,
  });

  factory Mission.fromJson(Map<String, dynamic> json) {
    return Mission(
      id: json['id'],
      title: json['title'],
      description: json['description'],
      rewardXp: json['reward_xp'] ?? 10,
      missionType: json['mission_type'],
      targetAction: json['target_action'],
      targetValue: json['target_value'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class UserMission {
  final int id;
  final int userId;
  final int missionId;
  final int progress;
  final bool isCompleted;
  final DateTime createdAt;
  final Mission mission;

  UserMission({
    required this.id,
    required this.userId,
    required this.missionId,
    this.progress = 0,
    this.isCompleted = false,
    required this.createdAt,
    required this.mission,
  });

  factory UserMission.fromJson(Map<String, dynamic> json) {
    return UserMission(
      id: json['id'],
      userId: json['user_id'],
      missionId: json['mission_id'],
      progress: json['progress'] ?? 0,
      isCompleted: json['is_completed'] ?? false,
      createdAt: DateTime.parse(json['created_at']),
      mission: Mission.fromJson(json['mission']),
    );
  }
}

class LeaderboardEntry {
  final int userId;
  final String? fullName;
  final String? avatarUrl;
  final int totalXp;
  final int level;

  LeaderboardEntry({
    required this.userId,
    this.fullName,
    this.avatarUrl,
    required this.totalXp,
    required this.level,
  });

  factory LeaderboardEntry.fromJson(Map<String, dynamic> json) {
    return LeaderboardEntry(
      userId: json['user_id'],
      fullName: json['full_name'],
      avatarUrl: json['avatar_url'],
      totalXp: json['total_xp'],
      level: json['level'],
    );
  }
}

class GamificationStatus {
  final int totalXp;
  final int level;
  final int currentStreak;
  final int longestStreak;
  final int achievementsCount;
  final int completedMissionsToday;

  GamificationStatus({
    required this.totalXp,
    required this.level,
    required this.currentStreak,
    required this.longestStreak,
    required this.achievementsCount,
    required this.completedMissionsToday,
  });

  factory GamificationStatus.fromJson(Map<String, dynamic> json) {
    return GamificationStatus(
      totalXp: json['total_xp'],
      level: json['level'],
      currentStreak: json['current_streak'],
      longestStreak: json['longest_streak'],
      achievementsCount: json['achievements_count'],
      completedMissionsToday: json['completed_missions_today'],
    );
  }
}
