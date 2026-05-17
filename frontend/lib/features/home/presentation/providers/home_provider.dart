import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:ai_english_coach/features/home/models/dashboard_model.dart';

import 'package:ai_english_coach/features/auth/services/auth_service.dart';

import 'package:ai_english_coach/features/auth/presentation/providers/auth_provider.dart';
import 'package:ai_english_coach/core/api_config.dart';


class HomeNotifier extends StateNotifier<AsyncValue<DashboardStats>> {
  final AuthService _authService;

  HomeNotifier(this._authService) : super(const AsyncValue.loading()) {
    fetchStats();
  }

  Future<void> fetchStats() async {
    state = const AsyncValue.loading();
    try {
      final token = await _authService.getAccessToken();
      if (token == null) {
        state = AsyncValue.error('Not authenticated', StackTrace.current);
        return;
      }

      final response = await http.get(
        Uri.parse(ApiConfig.dashboardStats),

        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        state = AsyncValue.data(DashboardStats.fromJson(data));
      } else {
        state = AsyncValue.error('Failed to load stats: ${response.statusCode}', StackTrace.current);
      }
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }
}

final homeProvider = StateNotifierProvider<HomeNotifier, AsyncValue<DashboardStats>>((ref) {
  final authService = ref.watch(authServiceProvider);
  // Watch authProvider to trigger rebuild when user changes (login/logout)
  ref.watch(authProvider);
  return HomeNotifier(authService);
});
