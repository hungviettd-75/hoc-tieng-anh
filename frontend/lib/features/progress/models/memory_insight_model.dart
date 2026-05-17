class MemoryInsight {
  final List<StructuredMemory> structuredMemories;
  final List<String> aiInsights;
  final List<TimelineEvent> timeline;

  MemoryInsight({
    required this.structuredMemories,
    required this.aiInsights,
    required this.timeline,
  });

  factory MemoryInsight.fromJson(Map<String, dynamic> json) {
    return MemoryInsight(
      structuredMemories: (json['structured_memories'] as List)
          .map((i) => StructuredMemory.fromJson(i))
          .toList(),
      aiInsights: List<String>.from(json['ai_insights']),
      timeline: (json['timeline'] as List)
          .map((i) => TimelineEvent.fromJson(i))
          .toList(),
    );
  }
}

class StructuredMemory {
  final String key;
  final String value;
  final double importance;
  final DateTime updatedAt;

  StructuredMemory({
    required this.key,
    required this.value,
    required this.importance,
    required this.updatedAt,
  });

  factory StructuredMemory.fromJson(Map<String, dynamic> json) {
    return StructuredMemory(
      key: json['key'],
      value: json['value'],
      importance: (json['importance'] as num).toDouble(),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}

class TimelineEvent {
  final String date;
  final String event;
  final String type; // goal, achievement, activity

  TimelineEvent({
    required this.date,
    required this.event,
    required this.type,
  });

  factory TimelineEvent.fromJson(Map<String, dynamic> json) {
    return TimelineEvent(
      date: json['date'],
      event: json['event'],
      type: json['type'],
    );
  }
}
