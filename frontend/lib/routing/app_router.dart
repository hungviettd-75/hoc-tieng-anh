import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/home/presentation/pages/home_page.dart';
import '../features/chat/presentation/pages/chat_page.dart';
import '../features/progress/presentation/pages/progress_page.dart';
import '../features/profile/presentation/pages/profile_page.dart';
import '../features/profile/presentation/pages/settings_page.dart';
import '../features/profile/presentation/pages/notification_settings_page.dart';
import '../features/profile/presentation/pages/support_center_page.dart';
import '../features/learn/presentation/pages/learn_page.dart';
import '../features/learn/presentation/pages/vocabulary_list_page.dart';
import '../features/learn/presentation/pages/lesson_detail_page.dart';
import '../features/learn/models/learning_models.dart' as learn_models;
import '../features/auth/presentation/pages/login_page.dart';
import '../features/auth/presentation/pages/register_page.dart';
import '../features/auth/presentation/providers/auth_provider.dart';
import '../features/chat/presentation/pages/voice_conversation_page.dart';
import '../features/speaking/presentation/pages/speaking_page.dart';
import '../features/speaking/presentation/pages/pronunciation_practice_page.dart';
import '../features/speaking/presentation/pages/pronunciation_result_page.dart';
import '../features/speaking/presentation/pages/ielts_page.dart';
import '../features/speaking/models/pronunciation_models.dart';
import '../widgets/main_scaffold.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>();
final GlobalKey<NavigatorState> _shellNavigatorKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);
  
  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/login',
    redirect: (context, state) {
      final isLoggedIn = authState.user != null;
      final isLoggingIn = state.uri.toString() == '/login' || state.uri.toString() == '/register';
      
      if (!isLoggedIn && !isLoggingIn) return '/login';
      if (isLoggedIn && isLoggingIn) return '/';
      
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterPage(),
      ),
      GoRoute(
        path: '/voice-chat',
        builder: (context, state) {
          final mode = state.uri.queryParameters['mode'];
          final level = state.uri.queryParameters['level'];
          final topic = state.uri.queryParameters['topic'];
          final words = state.uri.queryParameters['words'];
          return VoiceConversationPage(mode: mode, level: level, topic: topic, words: words);
        },
      ),
      // Speaking practice & result - fullscreen (ngoài ShellRoute)
      GoRoute(
        path: '/speaking/practice',
        builder: (context, state) {
          if (state.extra == null) {
            // Nếu mất dữ liệu (do nhấn back trình duyệt), quay về trang chủ speaking
            Future.microtask(() => context.go('/speaking'));
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          }
          final sentence = state.extra as PracticeSentence;
          return PronunciationPracticePage(sentence: sentence);
        },
      ),
      GoRoute(
        path: '/speaking/result',
        builder: (context, state) {
          if (state.extra == null) {
            Future.microtask(() => context.go('/speaking'));
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          }
          final result = state.extra as PronunciationResult;
          return PronunciationResultPage(result: result);
        },
      ),
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (context, state, child) {
          return MainScaffold(child: child);
        },
        routes: [
          GoRoute(
            path: '/',
            builder: (context, state) => const HomePage(),
          ),
          GoRoute(
            path: '/speaking',
            builder: (context, state) => const SpeakingPage(),
          ),
          GoRoute(
            path: '/chat',
            builder: (context, state) {
              final mode = state.uri.queryParameters['mode'];
              final level = state.uri.queryParameters['level'];
              final topic = state.uri.queryParameters['topic'];
              final words = state.uri.queryParameters['words'];
              return ChatPage(mode: mode, level: level, topic: topic, words: words);
            },
          ),
          GoRoute(
            path: '/progress',
            builder: (context, state) => const ProgressPage(),
          ),
          GoRoute(
            path: '/learn',
            builder: (context, state) => const LearnPage(),
            routes: [
              GoRoute(
                path: 'lesson',
                builder: (context, state) {
                  if (state.extra == null) {
                    // Nếu mất dữ liệu (do nhấn back trình duyệt hoặc refresh), quay về trang Lộ trình cá nhân
                    Future.microtask(() => context.go('/learn'));
                    return const Scaffold(body: Center(child: CircularProgressIndicator()));
                  }
                  final recommendation = state.extra as learn_models.RecommendationItem;
                  return LessonDetailPage(recommendation: recommendation);
                },
              ),
            ],
          ),
          GoRoute(
            path: '/profile',
            builder: (context, state) => const ProfilePage(),
          ),
          GoRoute(
            path: '/settings',
            builder: (context, state) => const SettingsPage(),
          ),
          GoRoute(
            path: '/notifications',
            builder: (context, state) => const NotificationSettingsPage(),
          ),
          GoRoute(
            path: '/support',
            builder: (context, state) => const SupportCenterPage(),
          ),
          GoRoute(
            path: '/ielts',
            builder: (context, state) => const IELTSPage(),
          ),
          GoRoute(
            path: '/vocabulary-list',
            builder: (context, state) => const VocabularyListPage(),
          ),
        ],
      ),
    ],
  );
});

