import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:ai_english_coach/features/gamification/models/gamification_models.dart';

import 'package:ai_english_coach/features/auth/services/auth_service.dart';
import 'package:ai_english_coach/features/auth/presentation/providers/auth_provider.dart';

class GamificationNotifier extends StateNotifier<AsyncValue<GamificationStatus>> {
  final AuthService _authService;

  GamificationNotifier(this._authService) : super(const AsyncValue.loading()) {
    fetchStatus();
  }

  Future<void> fetchStatus() async {
    state = const AsyncValue.loading();
    try {
      final token = await _authService.getAccessToken();
      if (token == null) {
        state = AsyncValue.error('Not authenticated', StackTrace.current);
        return;
      }

      final response = await http.get(
        Uri.parse('http://localhost:8000/api/v1/gamification/status'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        state = AsyncValue.data(GamificationStatus.fromJson(data));
      } else {
        state = AsyncValue.error('Failed to load status: ${response.statusCode}', StackTrace.current);
      }
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<bool> addXp(int amount) async {
    try {
      final token = await _authService.getAccessToken();
      if (token == null) return false;

      final response = await http.post(
        Uri.parse('http://localhost:8000/api/v1/gamification/add_xp?amount=$amount'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );
      if (response.statusCode == 200) {
        await fetchStatus();
        return true;
      }
    } catch (e) {
      // Handle error
    }
    return false;
  }
}

final gamificationProvider = StateNotifierProvider<GamificationNotifier, AsyncValue<GamificationStatus>>((ref) {
  // Watch authProvider to trigger rebuild when user changes (login/logout)
  ref.watch(authProvider);
  return GamificationNotifier(AuthService());
});

final leaderboardProvider = FutureProvider<List<LeaderboardEntry>>((ref) async {
  // Watch authProvider
  ref.watch(authProvider);
  final authService = AuthService();
  final token = await authService.getAccessToken();
  if (token == null) throw Exception('Not authenticated');

  final response = await http.get(
    Uri.parse('http://localhost:8000/api/v1/gamification/leaderboard'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
  );
  if (response.statusCode == 200) {
    final List<dynamic> data = jsonDecode(response.body);
    return data.map((e) => LeaderboardEntry.fromJson(e)).toList();
  } else {
    throw Exception('Failed to load leaderboard: ${response.statusCode}');
  }
});

final missionsProvider = FutureProvider<List<UserMission>>((ref) async {
  // Watch authProvider
  ref.watch(authProvider);
  final authService = AuthService();
  final token = await authService.getAccessToken();
  if (token == null) throw Exception('Not authenticated');

  final response = await http.get(
    Uri.parse('http://localhost:8000/api/v1/gamification/missions'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
  );
  if (response.statusCode == 200) {
    final List<dynamic> data = jsonDecode(response.body);
    return data.map((e) => UserMission.fromJson(e)).toList();
  } else {
    throw Exception('Failed to load missions: ${response.statusCode}');
  }
});
