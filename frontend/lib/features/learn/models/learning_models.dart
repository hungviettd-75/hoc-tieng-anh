class SkillLevel {
  final double vocabulary;
  final double grammar;
  final double pronunciation;
  final double listening;
  final double fluency;

  SkillLevel({
    required this.vocabulary,
    required this.grammar,
    required this.pronunciation,
    required this.listening,
    required this.fluency,
  });

  factory SkillLevel.fromJson(Map<String, dynamic> json) {
    return SkillLevel(
      vocabulary: (json['vocabulary'] as num?)?.toDouble() ?? 0.0,
      grammar: (json['grammar'] as num?)?.toDouble() ?? 0.0,
      pronunciation: (json['pronunciation'] as num?)?.toDouble() ?? 0.0,
      listening: (json['listening'] as num?)?.toDouble() ?? 0.0,
      fluency: (json['fluency'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class WeakPoint {
  final int id;
  final String category;
  final String description;
  final int frequency;

  WeakPoint({
    required this.id,
    required this.category,
    required this.description,
    required this.frequency,
  });

  factory WeakPoint.fromJson(Map<String, dynamic> json) {
    return WeakPoint(
      id: json['id'] as int,
      category: json['category'] as String? ?? '',
      description: json['description'] as String? ?? '',
      frequency: json['frequency'] as int? ?? 1,
    );
  }
}

class RecommendationItem {
  final String id;
  final String topic;
  final String contentType;
  final String difficultyLevel;
  final int estimatedMinutes;
  final String description;
  final String reason;

  RecommendationItem({
    required this.id,
    required this.topic,
    required this.contentType,
    required this.difficultyLevel,
    required this.estimatedMinutes,
    required this.description,
    required this.reason,
  });

  factory RecommendationItem.fromJson(Map<String, dynamic> json) {
    return RecommendationItem(
      id: json['id'] as String? ?? '',
      topic: json['topic'] as String? ?? '',
      contentType: json['content_type'] as String? ?? '',
      difficultyLevel: json['difficulty_level'] as String? ?? '',
      estimatedMinutes: json['estimated_minutes'] as int? ?? 5,
      description: json['description'] as String? ?? '',
      reason: json['reason'] as String? ?? '',
    );
  }
}

class LearningDashboardData {
  final SkillLevel skillLevel;
  final List<WeakPoint> weakPoints;
  final List<RecommendationItem> recommendations;

  LearningDashboardData({
    required this.skillLevel,
    required this.weakPoints,
    required this.recommendations,
  });

  factory LearningDashboardData.fromJson(Map<String, dynamic> json) {
    return LearningDashboardData(
      skillLevel: SkillLevel.fromJson(json['skill_level'] ?? {}),
      weakPoints: (json['weak_points'] as List<dynamic>?)
              ?.map((e) => WeakPoint.fromJson(e))
              .toList() ??
          [],
      recommendations: (json['daily_recommendations'] as List<dynamic>?)
              ?.map((e) => RecommendationItem.fromJson(e))
              .toList() ??
          [],
    );
  }
}
