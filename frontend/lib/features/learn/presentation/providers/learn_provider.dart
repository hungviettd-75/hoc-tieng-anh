import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/learning_models.dart';
import '../../services/learn_service.dart';

final learnServiceProvider = Provider<LearnService>((ref) {
  return LearnService();
});

final learningDashboardProvider = FutureProvider<LearningDashboardData>((ref) async {
  final service = ref.read(learnServiceProvider);
  return await service.getDashboardData();
});
