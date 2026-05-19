import 'dart:async';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ai_english_coach/services/chat_service.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:ai_english_coach/core/api_config.dart';
import 'chat_provider.dart';

enum AIStatus { idle, thinking, speaking, correcting }

class RealtimeCorrection {
  final String original;
  final String correction;
  final String ipa;
  final String explanationVi;

  RealtimeCorrection({
    required this.original,
    required this.correction,
    required this.ipa,
    required this.explanationVi,
  });

  factory RealtimeCorrection.fromJson(Map<String, dynamic> json) {
    return RealtimeCorrection(
      original: json['original'] ?? '',
      correction: json['correction'] ?? '',
      ipa: json['ipa'] ?? '',
      explanationVi: json['explanation_vi'] ?? '',
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

  RealtimeChatState({
    required this.messages,
    this.status = AIStatus.idle,
    this.currentSubtitle = '',
    this.lastGrammarCorrection,
    this.currentCorrections = const [],
    this.formattedCorrectionText = '',
  });

  RealtimeChatState copyWith({
    List<ChatMessage>? messages,
    AIStatus? status,
    String? currentSubtitle,
    String? lastGrammarCorrection,
    List<RealtimeCorrection>? currentCorrections,
    String? formattedCorrectionText,
  }) {
    return RealtimeChatState(
      messages: messages ?? this.messages,
      status: status ?? this.status,
      currentSubtitle: currentSubtitle ?? this.currentSubtitle,
      lastGrammarCorrection: lastGrammarCorrection ?? this.lastGrammarCorrection,
      currentCorrections: currentCorrections ?? this.currentCorrections,
      formattedCorrectionText: formattedCorrectionText ?? this.formattedCorrectionText,
    );
  }
}

class RealtimeChatNotifier extends StateNotifier<RealtimeChatState> {
  final ChatService _chatService;
  final AudioPlayer _audioPlayer = AudioPlayer();
  StreamSubscription? _subscription;

  RealtimeChatNotifier(this._chatService) : super(RealtimeChatState(messages: []));

  String _sanitizeTtsText(String text) {
    String sanitized = text;

    // 1. Loại bỏ gợi ý tiếng Việt bọc trong dấu ngoặc đơn dạng *(Gợi ý:...)*
    sanitized = sanitized.replaceAll(RegExp(r'\*?\(gợi ý:[^\)]*\)\*?', caseSensitive: false), '');
    sanitized = sanitized.replaceAll(RegExp(r'\*?\(gợi ý thực hành:[^\)]*\)\*?', caseSensitive: false), '');
    
    // 2. Loại bỏ các cặp dấu ngoặc đơn chứa giải thích hoặc hướng dẫn phụ trợ dạng *(...)*
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

  final List<String> _speechQueue = [];
  bool _isSpeaking = false;

  Future<void> _speakBilingual(String text) async {
    final sanitizedText = _sanitizeTtsText(text);
    if (sanitizedText.isEmpty) return;
    
    _speechQueue.add(sanitizedText);
    if (_isSpeaking) return;

    _processNextInQueue();
  }

  Future<void> _processNextInQueue() async {
    if (_speechQueue.isEmpty) {
      _isSpeaking = false;
      return;
    }

    _isSpeaking = true;
    final text = _speechQueue.removeAt(0);
    print('DEBUG: Speaking: "$text"');

    try {
      final url = '${ApiConfig.speaking}/tts?text=${Uri.encodeComponent(text)}';
      
      final completer = Completer<void>();
      late StreamSubscription subscription;
      
      // Timeout 15 giây để tránh treo hàng đợi
      Timer? timeoutTimer;

      subscription = _audioPlayer.onPlayerComplete.listen((_) {
        timeoutTimer?.cancel();
        subscription.cancel();
        if (!completer.isCompleted) completer.complete();
      });

      timeoutTimer = Timer(const Duration(seconds: 15), () {
        print('DEBUG: Audio playback timeout');
        subscription.cancel();
        if (!completer.isCompleted) completer.complete();
      });

      await _audioPlayer.stop(); // Dừng câu trước nếu còn đang phát
      await _audioPlayer.play(UrlSource(url));
      await completer.future;
    } catch (e) {
      print('ERROR playing audio: $e');
    } finally {
      // Đợi một chút trước khi sang câu tiếp theo cho tự nhiên
      await Future.delayed(const Duration(milliseconds: 300));
      _processNextInQueue();
    }
  }


  void connectWithContext({String? mode, String? level, String? topic, String? words}) {
    print('DEBUG: Reconnecting to Realtime chat WebSocket with mode: $mode, level: $level, topic: $topic, words: $words');
    _subscription?.cancel();
    _chatService.disconnect();
    state = RealtimeChatState(messages: [], status: AIStatus.idle);
    _chatService.connectRealtime(1, mode: mode, level: level, topic: topic, words: words);
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
        
        state = state.copyWith(currentSubtitle: state.currentSubtitle + content);
        // HOÀN TOÀN KHÔNG ĐỌC DELTA (Ô CHAT) THEO YÊU CẦU NGƯỜI DÙNG
        
      } else if (type == 'realtime_correction') {
        final correctionsJson = decoded['corrections'] as List;
        final formattedText = decoded['formatted_text'] ?? '';
        final corrections = correctionsJson.map((c) => RealtimeCorrection.fromJson(c)).toList();
        
        state = state.copyWith(
          status: AIStatus.correcting,
          currentCorrections: corrections,
          formattedCorrectionText: formattedText,
        );
        
        // Thẻ vàng AI Correction sẽ chỉ hiển thị trực quan bằng mắt, không đọc bằng âm thanh để tránh làm loãng hội thoại và xung đột luồng audio
      } else if (type == 'done') {
        final fullContent = decoded['full_content'] ?? '';
        final grammarNotes = decoded['grammar_notes'];
        final routeUsed = decoded['route_used'];
        
        final aiMessage = ChatMessage(
          content: fullContent,
          isAI: true,
          grammarNotes: grammarNotes,
        );
        
        state = state.copyWith(
          messages: [...state.messages, aiMessage],
          lastGrammarCorrection: grammarNotes,
          status: AIStatus.idle,
        );
        
        // Luôn luôn cất giọng đọc câu phản hồi của AI để duy trì đàm thoại liên tục!
        // Hàng đợi _speechQueue sẽ tự động phát tuần tự sau khi đọc xong sửa lỗi tiếng Việt (nếu có).
        if (fullContent.isNotEmpty) {
          _speakBilingual(fullContent);
        }
      }
    });

    // Báo Server là Client đã kết nối hoàn tất và sẵn sàng lắng nghe!
    Future.delayed(const Duration(milliseconds: 300), () {
      _chatService.sendRealtimeAction({
        "type": "client_ready"
      });
      print('DEBUG: Sent client_ready to Server');
    });
  }

  void sendVoiceMessage(String text) {
    if (text.trim().isEmpty) return;
    
    final userMessage = ChatMessage(content: text, isAI: false);
    state = state.copyWith(
      messages: [...state.messages, userMessage],
      currentSubtitle: '...', // Reset subtitle for AI response
      currentCorrections: [],
      formattedCorrectionText: '',
    );
    
    _chatService.sendRealtimeAction({
      "type": "message",
      "content": text,
    });
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _chatService.disconnect();
    _audioPlayer.stop();
    _audioPlayer.dispose();
    super.dispose();
  }
}

final realtimeChatProvider = StateNotifierProvider<RealtimeChatNotifier, RealtimeChatState>((ref) {
  return RealtimeChatNotifier(ref.watch(chatServiceProvider));
});
