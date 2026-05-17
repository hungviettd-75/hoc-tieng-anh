/// Data models cho Pronunciation Scoring system.

class PronunciationResult {
  final int sessionId;
  final double overallScore;
  final double fluencyScore;
  final double pronunciationScore;
  final double confidenceScore;
  final double intonationScore;
  final String targetText;
  final String transcribedText;
  final List<WordScore> wordScores;
  final String feedback;

  PronunciationResult({
    required this.sessionId,
    required this.overallScore,
    required this.fluencyScore,
    required this.pronunciationScore,
    required this.confidenceScore,
    required this.intonationScore,
    required this.targetText,
    required this.transcribedText,
    required this.wordScores,
    required this.feedback,
  });

  factory PronunciationResult.fromJson(Map<String, dynamic> json) {
    final metrics = json['metrics'] as List<dynamic>? ?? [];
    
    double getMetric(String name) {
      try {
        final m = metrics.firstWhere(
          (e) => e is Map && e['metric'] == name,
          orElse: () => null,
        );
        if (m == null) return 0.0;
        final score = m['score'];
        if (score is num) return score.toDouble();
        if (score is String) return double.tryParse(score) ?? 0.0;
        return 0.0;
      } catch (e) {
        return 0.0;
      }
    }

    return PronunciationResult(
      sessionId: json['session_id'] ?? 0,
      overallScore: (json['overall_score'] as num?)?.toDouble() ?? 0.0,
      fluencyScore: getMetric('fluency'),
      pronunciationScore: getMetric('pronunciation'),
      confidenceScore: getMetric('confidence'),
      intonationScore: getMetric('intonation'),
      targetText: json['target_text'] ?? '',
      transcribedText: json['transcribed_text'] ?? '',
      wordScores: (json['word_scores'] as List<dynamic>? ?? [])
          .map((w) => WordScore.fromJson(w))
          .toList(),
      feedback: json['feedback'] ?? '',
    );
  }
}

class WordScore {
  final String word;
  final bool isCorrect;
  final double confidence;

  WordScore({
    required this.word,
    required this.isCorrect,
    required this.confidence,
  });

  factory WordScore.fromJson(Map<String, dynamic> json) {
    return WordScore(
      word: json['word'] ?? '',
      isCorrect: json['is_correct'] ?? false,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class PracticeSentence {
  final int id;
  final String text;
  final String level;
  final String category;

  PracticeSentence({
    required this.id,
    required this.text,
    required this.level,
    required this.category,
  });

  factory PracticeSentence.fromJson(Map<String, dynamic> json) {
    return PracticeSentence(
      id: json['id'] ?? 0,
      text: json['text'] ?? '',
      level: json['level'] ?? 'A1',
      category: json['category'] ?? 'general',
    );
  }
}

class PronunciationHistory {
  final List<PronunciationSessionSummary> sessions;
  final int totalSessions;
  final double averageScore;

  PronunciationHistory({
    required this.sessions,
    required this.totalSessions,
    required this.averageScore,
  });

  factory PronunciationHistory.fromJson(Map<String, dynamic> json) {
    return PronunciationHistory(
      sessions: (json['sessions'] as List<dynamic>? ?? [])
          .map((s) => PronunciationSessionSummary.fromJson(s))
          .toList(),
      totalSessions: json['total_sessions'] ?? 0,
      averageScore: (json['average_score'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class PronunciationSessionSummary {
  final int id;
  final String targetText;
  final String? transcribedText;
  final double overallScore;
  final DateTime? createdAt;

  PronunciationSessionSummary({
    required this.id,
    required this.targetText,
    this.transcribedText,
    required this.overallScore,
    this.createdAt,
  });

  factory PronunciationSessionSummary.fromJson(Map<String, dynamic> json) {
    return PronunciationSessionSummary(
      id: json['id'] ?? 0,
      targetText: json['target_text'] ?? '',
      transcribedText: json['transcribed_text'],
      overallScore: (json['overall_score'] as num?)?.toDouble() ?? 0.0,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'])
          : null,
    );
  }
}
