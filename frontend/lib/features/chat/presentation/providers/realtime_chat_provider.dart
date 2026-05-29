import 'dart:async';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ai_english_coach/services/chat_service.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:ai_english_coach/core/api_config.dart';
import 'chat_provider.dart';
import 'package:ai_english_coach/features/auth/presentation/providers/auth_provider.dart';
import 'package:http/http.dart' as http;

enum AIStatus { idle, thinking, speaking, correcting }

class RealtimeCorrection {
  final String original;
  final String correction;
  final String ipa;
  final String explanationVi;
  final String errorType;

  RealtimeCorrection({
    required this.original,
    required this.correction,
    required this.ipa,
    required this.explanationVi,
    required this.errorType,
  });

  factory RealtimeCorrection.fromJson(Map<String, dynamic> json) {
    return RealtimeCorrection(
      original: json['original'] ?? '',
      correction: json['correction'] ?? '',
      ipa: json['ipa'] ?? '',
      explanationVi: json['explanation_vi'] ?? '',
      errorType: json['error_type'] ?? 'grammar',
    );
  }
}

class RealtimeChatState {
  final List<ChatMessage> messages;
  final AIStatus status;
  final String currentSubtitle;
  final String? lastGrammarCorrection;
  final List<RealtimeCorrection> currentCorrections;
  final String formattedCorrectionText;
  final DateTime? sessionStartTime;
  final int sentenceCount;
  final int pronunciationErrorsCount;
  final int grammarErrorsCount;
  final List<RealtimeCorrection> allSessionMistakes;
  final bool isTtsSpeaking;

  RealtimeChatState({
    required this.messages,
    this.status = AIStatus.idle,
    this.currentSubtitle = '',
    this.lastGrammarCorrection,
    this.currentCorrections = const [],
    this.formattedCorrectionText = '',
    this.sessionStartTime,
    this.sentenceCount = 0,
    this.pronunciationErrorsCount = 0,
    this.grammarErrorsCount = 0,
    this.allSessionMistakes = const [],
    this.isTtsSpeaking = false,
  });

  RealtimeChatState copyWith({
    List<ChatMessage>? messages,
    AIStatus? status,
    String? currentSubtitle,
    String? lastGrammarCorrection,
    List<RealtimeCorrection>? currentCorrections,
    String? formattedCorrectionText,
    DateTime? sessionStartTime,
    int? sentenceCount,
    int? pronunciationErrorsCount,
    int? grammarErrorsCount,
    List<RealtimeCorrection>? allSessionMistakes,
    bool? isTtsSpeaking,
  }) {
    return RealtimeChatState(
      messages: messages ?? this.messages,
      status: status ?? this.status,
      currentSubtitle: currentSubtitle ?? this.currentSubtitle,
      lastGrammarCorrection: lastGrammarCorrection ?? this.lastGrammarCorrection,
      currentCorrections: currentCorrections ?? this.currentCorrections,
      formattedCorrectionText: formattedCorrectionText ?? this.formattedCorrectionText,
      sessionStartTime: sessionStartTime ?? this.sessionStartTime,
      sentenceCount: sentenceCount ?? this.sentenceCount,
      pronunciationErrorsCount: pronunciationErrorsCount ?? this.pronunciationErrorsCount,
      grammarErrorsCount: grammarErrorsCount ?? this.grammarErrorsCount,
      allSessionMistakes: allSessionMistakes ?? this.allSessionMistakes,
      isTtsSpeaking: isTtsSpeaking ?? this.isTtsSpeaking,
    );
  }
}

class RealtimeChatNotifier extends StateNotifier<RealtimeChatState> {
  final ChatService _chatService;
  final Ref _ref;
  final AudioPlayer _audioPlayer = AudioPlayer();
  StreamSubscription? _subscription;
  bool _skipWelcome = false;
  Timer? _nudgeTimer;
  String? _currentMode;
  bool _stopped = false; // Flag chặn hoàn toàn speech queue khi thoát
  Completer<void>? _activeCompleter; // Để release completer đang chờ audio khi thoát

  RealtimeChatNotifier(this._chatService, this._ref) : super(RealtimeChatState(messages: []));

  String _sanitizeTtsText(String text) {
    String sanitized = text;

    // 0. Loại bỏ hoàn toàn phần gợi ý câu trả lời dành cho học viên (như "Bạn có thể nói: ...", "You can say: ...", v.v. cho đến hết chuỗi)
    // Điều này giúp giữ lại phần gợi ý trên màn hình cho học viên nhìn, nhưng AI phát âm TTS sẽ KHÔNG đọc phần gợi ý này để học viên tự luyện tập.
    sanitized = sanitized.replaceAll(RegExp(r'(?:💡\s*)?(?:bạn\s+có\s+thể\s+nói|bạn\s+có\s+thể\s+trả\s+lời|gợi\s+ý\s+nói|gợi\s+ý\s+trả\s+lời|gợi\s+ý\s+thực\s+hành|you\s+can\s+say|you\s+can\s+answer|suggested\s+response|suggested\s+answer)[\s\S]*$', caseSensitive: false), '');

    // 1. Loại bỏ gợi ý tiếng Việt bọc trong dấu ngoặc đơn dạng *(Gợi ý:...)*
    sanitized = sanitized.replaceAll(RegExp(r'\*?\(gợi ý:[^\)]*\)\*?', caseSensitive: false), '');
    sanitized = sanitized.replaceAll(RegExp(r'\*?\(gợi ý thực hành:[^\)]*\)\*?', caseSensitive: false), '');
    
    // 2. Loại bỏ hoàn toàn các cặp dấu ngoặc đơn chứa giải thích, hướng dẫn phụ trợ hoặc dịch nghĩa tiếng Việt dạng *(...)* để AI chỉ cất giọng đọc tiếng Anh chuẩn bản xứ
    sanitized = sanitized.replaceAll(RegExp(r'\*?\([^\)]*\)\*?'), '');

    // 3. Loại bỏ ký tự định dạng Markdown
    sanitized = sanitized.replaceAll('**', '');
    sanitized = sanitized.replaceAll('*', '');
    sanitized = sanitized.replaceAll('_', '');
    sanitized = sanitized.replaceAll('`', '');

    // 4. Loại bỏ các tiền tố hội thoại để giọng đọc AI tự nhiên hơn
    sanitized = sanitized.replaceAll(RegExp(r'^(waiter|customer|coach|student|ai|user):\s*', caseSensitive: false), '');

    // 5. Chuẩn hóa khoảng trắng và loại bỏ xuống dòng gây lỗi URL
    sanitized = sanitized.replaceAll(RegExp(r'\n+'), ' ');
    sanitized = sanitized.replaceAll(RegExp(r'\s+'), ' ');

    return sanitized.trim();
  }

  String _sanitizeDisplaySubtitle(String text) {
    String sanitized = text;

    // Loại bỏ ký tự định dạng Markdown để hiển thị sạch trên Flutter Text widget
    sanitized = sanitized.replaceAll('**', '');
    sanitized = sanitized.replaceAll('*', '');
    sanitized = sanitized.replaceAll('_', '');
    sanitized = sanitized.replaceAll('`', '');

    // Loại bỏ các tiền tố hội thoại để giao diện tự nhiên
    sanitized = sanitized.replaceAll(RegExp(r'^(waiter|customer|coach|student|ai|user):\s*', caseSensitive: false), '');

    // Chuẩn hóa khoảng trắng và loại bỏ xuống dòng thừa gây lỗi UI
    sanitized = sanitized.replaceAll(RegExp(r'\n+'), ' ');
    sanitized = sanitized.replaceAll(RegExp(r'\s+'), ' ');

    return sanitized.trim();
  }

  final List<String> _speechQueue = [];
  bool _isSpeaking = false;

  Future<void> _speakBilingual(String text) async {
    if (_stopped) return; // Không thêm vào queue nếu đã dừng
    final sanitizedText = _sanitizeTtsText(text);
    if (sanitizedText.isEmpty) return;
    
    _speechQueue.add(sanitizedText);
    if (_isSpeaking) return;

    _processNextInQueue();
  }

  /// Khởi động Nudge Timer: Sau khi AI nói xong, nếu học viên im lặng 12 giây → AI tự động nhắc nhở
  void _startNudgeTimer() {
    _nudgeTimer?.cancel();
    _nudgeTimer = Timer(const Duration(seconds: 12), () {
      print('DEBUG: Nudge timer fired! Student has not responded in 12 seconds.');
      // Gửi tín hiệu nudge lên backend để AI chủ động hỏi lại
      _chatService.sendRealtimeAction({
        "type": "message",
        "content": "[SILENCE_NUDGE]",
      });
    });
  }

  /// Hủy Nudge Timer khi học viên bắt đầu nói
  void _cancelNudgeTimer() {
    _nudgeTimer?.cancel();
  }

  Future<void> _processNextInQueue() async {
    // Kiểm tra flag _stopped trước MỌI hành động - chặn triệt để vòng lặp đệ quy
    if (_stopped) {
      _isSpeaking = false;
      _speechQueue.clear();
      return;
    }

    if (_speechQueue.isEmpty) {
      _isSpeaking = false;
      state = state.copyWith(isTtsSpeaking: false);
      // Khi AI phát âm xong hoàn toàn, bắt đầu đếm thời gian chờ học viên phản hồi
      _startNudgeTimer();
      return;
    }

    _isSpeaking = true;
    state = state.copyWith(isTtsSpeaking: true);
    final text = _speechQueue.removeAt(0);
    print('DEBUG: Speaking: "$text"');

    try {
      // Kiểm tra lại flag trước khi thực sự phát âm
      if (_stopped) return;

      final url = '${ApiConfig.speaking}/tts?text=${Uri.encodeComponent(text)}';
      
      final completer = Completer<void>();
      _activeCompleter = completer; // Lưu reference để có thể release từ bên ngoài
      late StreamSubscription subscription;
      
      // Timeout 45 giây để thoải mái phát các câu chào/nhập vai dài và tránh treo hàng đợi
      Timer? timeoutTimer;

      subscription = _audioPlayer.onPlayerComplete.listen((_) {
        timeoutTimer?.cancel();
        subscription.cancel();
        if (!completer.isCompleted) completer.complete();
      });

      timeoutTimer = Timer(const Duration(seconds: 45), () {
        print('DEBUG: Audio playback timeout - stopping player');
        _audioPlayer.stop(); // Dừng audio player nếu bị treo/quá hạn
        subscription.cancel();
        if (!completer.isCompleted) completer.complete();
      });

      await _audioPlayer.stop(); // Dừng câu trước nếu còn đang phát
      
      // Kiểm tra flag lần cuối trước khi phát
      if (_stopped) {
        timeoutTimer?.cancel();
        subscription.cancel();
        if (!completer.isCompleted) completer.complete();
        return;
      }

      await _audioPlayer.play(UrlSource(url));
      await completer.future;
    } catch (e) {
      print('ERROR playing audio: $e');
    } finally {
      _activeCompleter = null;
      // Kiểm tra flag trước khi chuyển sang câu tiếp theo
      if (_stopped) {
        _isSpeaking = false;
        _speechQueue.clear();
        return;
      }
      // Đợi một chút trước khi sang câu tiếp theo cho tự nhiên
      await Future.delayed(const Duration(milliseconds: 300));
      _processNextInQueue();
    }
  }


  void connectWithContext({String? mode, String? level, String? topic, String? words, bool skipWelcome = false}) {
    print('DEBUG: Reconnecting to Realtime chat WebSocket with mode: $mode, level: $level, topic: $topic, words: $words, skipWelcome: $skipWelcome');
    _skipWelcome = skipWelcome;
    _currentMode = mode;
    _stopped = false; // Reset flag khi bắt đầu phiên mới
    _nudgeTimer?.cancel();
    _subscription?.cancel();
    _chatService.disconnect();
    state = RealtimeChatState(
      messages: [], 
      status: AIStatus.idle,
      sessionStartTime: DateTime.now(),
      sentenceCount: 0,
      pronunciationErrorsCount: 0,
      grammarErrorsCount: 0,
      allSessionMistakes: const [],
      isTtsSpeaking: false,
    );
    final user = _ref.read(authProvider).user;
    final userId = user?.id ?? 1;
    _chatService.connectRealtime(userId, mode: mode, level: level, topic: topic, words: words);
    _listenToMessages();
  }

  void _listenToMessages() {
    _subscription?.cancel();
    _subscription = _chatService.realtimeMessages.listen((data) {
      final decoded = jsonDecode(data);
      final type = decoded['type'];

      if (type == 'status') {
        final statusStr = decoded['status'];
        AIStatus newStatus = AIStatus.idle;
        if (statusStr == 'thinking') newStatus = AIStatus.thinking;
        if (statusStr == 'speaking') newStatus = AIStatus.speaking;
        if (statusStr == 'correcting') newStatus = AIStatus.correcting;
        state = state.copyWith(status: newStatus);
        
        if (newStatus == AIStatus.speaking) {
          state = state.copyWith(currentSubtitle: '');
        }
      } else if (type == 'delta') {
        final content = decoded['content'] ?? '';
        final isSilent = decoded['silent'] ?? false;
        
        if (!isSilent) {
          // Làm sạch nhanh markdown khi stream để hiển thị giao diện mượt mà và sạch sẽ
          final cleanContent = content.replaceAll('*', '').replaceAll('_', '').replaceAll('`', '');
          state = state.copyWith(currentSubtitle: state.currentSubtitle + cleanContent);
        }
        // HOÀN TOÀN KHÔNG ĐỌC DELTA (Ô CHAT) THEO YÊU CẦU NGƯỜI DÙNG
        
      } else if (type == 'realtime_correction') {
        final correctionsJson = decoded['corrections'] as List;
        final formattedText = decoded['formatted_text'] ?? '';
        final corrections = correctionsJson.map((c) => RealtimeCorrection.fromJson(c)).toList();
        
        int pErrors = corrections.where((c) => c.errorType == 'pronunciation').length;
        int gErrors = corrections.where((c) => c.errorType == 'grammar' || c.errorType == 'natural_speaking').length;
        
        state = state.copyWith(
          status: AIStatus.correcting,
          currentCorrections: corrections,
          formattedCorrectionText: formattedText,
          pronunciationErrorsCount: state.pronunciationErrorsCount + pErrors,
          grammarErrorsCount: state.grammarErrorsCount + gErrors,
          allSessionMistakes: [...state.allSessionMistakes, ...corrections],
        );
        
        // Thẻ vàng AI Correction sẽ chỉ hiển thị trực quan bằng mắt, không đọc bằng âm thanh để tránh làm loãng hội thoại và xung đột luồng audio
      } else if (type == 'done') {
        // Kiểm tra flag _stopped - nếu đã dừng thì không xử lý tin nhắn mới
        if (_stopped) return;

        final fullContent = decoded['full_content'] ?? '';
        final grammarNotes = decoded['grammar_notes'];
        final routeUsed = decoded['route_used'];
        
        final aiMessage = ChatMessage(
          content: fullContent,
          isAI: true,
          grammarNotes: grammarNotes,
        );
        
        // Làm sạch phụ đề hiển thị để sạch markdown nhưng VẪN GIỮ lại gợi ý câu trả lời cho học viên đọc
        final cleanedSubtitle = _sanitizeDisplaySubtitle(fullContent);
        
        state = state.copyWith(
          messages: [...state.messages, aiMessage],
          lastGrammarCorrection: grammarNotes,
          status: AIStatus.idle,
          currentSubtitle: cleanedSubtitle,
        );
        
        // Luôn luôn cất giọng đọc câu phản hồi của AI để duy trì đàm thoại liên tục!
        // Hàng đợi _speechQueue sẽ tự động phát tuần tự sau khi đọc xong sửa lỗi tiếng Việt (nếu có).
        if (fullContent.isNotEmpty && !_stopped) {
          _speakBilingual(fullContent);
        }
      }
    });

    // Báo Server là Client đã kết nối hoàn tất và sẵn sàng lắng nghe!
    Future.delayed(const Duration(milliseconds: 300), () {
      _chatService.sendRealtimeAction({
        "type": "client_ready",
        "skip_welcome": _skipWelcome
      });
      print('DEBUG: Sent client_ready to Server with skip_welcome: $_skipWelcome');
    });
  }

  void sendVoiceMessage(String text) {
    if (text.trim().isEmpty) return;
    
    // Học viên đã phản hồi → hủy nudge timer ngay lập tức
    _cancelNudgeTimer();
    
    final userMessage = ChatMessage(content: text, isAI: false);
    state = state.copyWith(
      messages: [...state.messages, userMessage],
      currentSubtitle: '...', // Reset subtitle for AI response
      currentCorrections: [],
      formattedCorrectionText: '',
      sentenceCount: state.sentenceCount + 1,
    );
    
    _chatService.sendRealtimeAction({
      "type": "message",
      "content": text,
    });
  }

  void speakWarning(String text) {
    _speakBilingual(text);
  }

  Future<Map<String, dynamic>?> endRoleplaySession(String topic, String level) async {
    final startTime = state.sessionStartTime ?? DateTime.now();
    final durationSeconds = DateTime.now().difference(startTime).inSeconds;
    final durationMinutes = (durationSeconds / 60.0).ceil();
    
    // Tính điểm số
    final pronunciationScore = (100.0 - state.pronunciationErrorsCount * 8.0).clamp(50.0, 100.0);
    final confidenceScore = (100.0 - (state.pronunciationErrorsCount + state.grammarErrorsCount) * 4.0).clamp(55.0, 100.0);
    final fluencyScore = (60.0 + state.sentenceCount * 5.0 - state.grammarErrorsCount * 5.0).clamp(50.0, 100.0);
    
    try {
      final authService = _ref.read(authServiceProvider);
      final token = await authService.getAccessToken();
      final headers = {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };
      
      final body = jsonEncode({
        'duration_minutes': durationMinutes,
        'sentence_count': state.sentenceCount,
        'pronunciation_errors_count': state.pronunciationErrorsCount,
        'grammar_errors_count': state.grammarErrorsCount,
        'pronunciation_score': pronunciationScore,
        'fluency_score': fluencyScore,
        'confidence_score': confidenceScore,
        'topic': topic,
        'level': level,
      });
      
      print('DEBUG: Saving roleplay session to backend with: $body');
      
      final response = await http.post(
        Uri.parse('${ApiConfig.baseUrl}/chat/roleplay/session'),
        headers: headers,
        body: body,
      ).timeout(const Duration(seconds: 10)); // Thêm timeout 10 giây để tránh treo vô hạn khi backend lỗi mạng
      
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        return {
          'duration_minutes': durationMinutes,
          'sentence_count': state.sentenceCount,
          'pronunciation_errors_count': state.pronunciationErrorsCount,
          'grammar_errors_count': state.grammarErrorsCount,
          'pronunciation_score': pronunciationScore,
          'fluency_score': fluencyScore,
          'confidence_score': confidenceScore,
          'xp_earned': decoded['xp_earned'] ?? 50,
          'total_xp': decoded['total_xp'] ?? 0,
          'level': decoded['level'] ?? 1,
          'leveled_up': decoded['leveled_up'] ?? false,
        };
      } else {
        print('ERROR saving session: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('ERROR saving roleplay session: $e');
    }
    
    // Fallback nếu có lỗi mạng
    return {
      'duration_minutes': durationMinutes,
      'sentence_count': state.sentenceCount,
      'pronunciation_errors_count': state.pronunciationErrorsCount,
      'grammar_errors_count': state.grammarErrorsCount,
      'pronunciation_score': pronunciationScore,
      'fluency_score': fluencyScore,
      'confidence_score': confidenceScore,
      'xp_earned': 50,
      'total_xp': 100,
      'level': 1,
      'leveled_up': false,
    };
  }

  void resetAndDisconnect() {
    print('DEBUG: resetAndDisconnect() called - stopping all audio and disconnecting');
    _stopped = true; // ĐẶT FLAG TRƯỚC TIÊN để chặn mọi xử lý tiếp theo
    _nudgeTimer?.cancel();
    _subscription?.cancel(); // Hủy lắng nghe WebSocket stream → không nhận tin nhắn mới
    _chatService.disconnect();
    _speechQueue.clear(); // Xóa hàng đợi speech
    _isSpeaking = false;
    
    // Release completer đang chờ audio (nếu có) để tránh treo Future
    if (_activeCompleter != null && !_activeCompleter!.isCompleted) {
      _activeCompleter!.complete();
    }
    _activeCompleter = null;
    
    // Dừng audio player SAU KHI đã release completer
    _audioPlayer.stop();
  }

  void stopSpeaking() {
    print('DEBUG: stopSpeaking() called');
    _stopped = true; // Đặt flag chặn
    _speechQueue.clear();
    _isSpeaking = false;
    
    // Release completer đang chờ
    if (_activeCompleter != null && !_activeCompleter!.isCompleted) {
      _activeCompleter!.complete();
    }
    _activeCompleter = null;
    
    _audioPlayer.stop();
    state = state.copyWith(isTtsSpeaking: false);
  }

  /// Gọi khi user nhấn "Hủy" trong dialog xác nhận thoát - cho phép AI tiếp tục hội thoại
  void resumeAfterCancel() {
    print('DEBUG: resumeAfterCancel() called - allowing AI to speak again');
    _stopped = false;
  }

  @override
  void dispose() {
    _stopped = true;
    _nudgeTimer?.cancel();
    _subscription?.cancel();
    _chatService.disconnect();
    _speechQueue.clear();
    
    if (_activeCompleter != null && !_activeCompleter!.isCompleted) {
      _activeCompleter!.complete();
    }
    _activeCompleter = null;
    
    _audioPlayer.stop();
    _audioPlayer.dispose();
    super.dispose();
  }
}

final realtimeChatProvider = StateNotifierProvider<RealtimeChatNotifier, RealtimeChatState>((ref) {
  return RealtimeChatNotifier(ref.watch(chatServiceProvider), ref);
});
