import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ai_english_coach/features/auth/services/auth_service.dart';
import 'package:ai_english_coach/features/auth/models/user_model.dart';

class AuthState {
  final UserModel? user;
  final bool isLoading;
  final String? error;

  AuthState({this.user, this.isLoading = false, this.error});

  AuthState copyWith({UserModel? user, bool? isLoading, String? error}) {
    return AuthState(
      user: user ?? this.user,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthService _authService;

  AuthNotifier(this._authService) : super(AuthState()) {
    checkAuth();
  }

  Future<void> checkAuth() async {
    final token = await _authService.getAccessToken();
    if (token != null) {
      state = state.copyWith(isLoading: true);
      try {
        final user = await _authService.getCurrentUser();
        state = state.copyWith(isLoading: false, user: user);
      } catch (e) {
        state = state.copyWith(isLoading: false);
        // Token có thể đã hết hạn hoặc không hợp lệ, không cần set error ở đây
        // để tránh hiện SnackBar lúc khởi động.
      }
    }
  }


  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true);
    try {
      await _authService.login(email, password);
      final user = await _authService.getCurrentUser();
      state = state.copyWith(isLoading: false, user: user);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> register(String email, String password, String fullName) async {
    state = state.copyWith(isLoading: true);
    try {
      await _authService.register(email, password, fullName);
      // Tự động đăng nhập sau khi đăng ký thành công
      await login(email, password);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void logout() {
    _authService.logout();
    state = AuthState();
  }
}

final authServiceProvider = Provider((ref) => AuthService());

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.watch(authServiceProvider));
});
