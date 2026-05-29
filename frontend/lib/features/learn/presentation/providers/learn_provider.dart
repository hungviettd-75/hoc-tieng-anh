import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ai_english_coach/features/auth/services/auth_service.dart';
import '../../models/learning_models.dart';
import '../../services/learn_service.dart';

final learnServiceProvider = Provider<LearnService>((ref) {
  return LearnService(AuthService());
});

final learningDashboardProvider = FutureProvider<LearningDashboardData>((ref) async {
  final service = ref.read(learnServiceProvider);
  return await service.getDashboardData();
});

// Quản lý trình độ từ vựng được chọn
final selectedLevelProvider = StateProvider<String>((ref) => 'B1');

// Quản lý chế độ học từ vựng được chọn (ví dụ: 'reading' hoặc 'matching')
final learningModeProvider = StateProvider<String?>((ref) => null);

