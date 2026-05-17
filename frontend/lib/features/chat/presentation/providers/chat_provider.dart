import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ai_english_coach/services/chat_service.dart';

// Model tin nhắn
class ChatMessage {
  final String content;
  final bool isAI;
  final String? grammarNotes;

  ChatMessage({required this.content, required this.isAI, this.grammarNotes});
}

// State cho Chat
class ChatState {
  final List<ChatMessage> messages;
  final bool isConnected;
  final String? error;

  ChatState({
    required this.messages,
    this.isConnected = false,
    this.error,
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isConnected,
    String? error,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isConnected: isConnected ?? this.isConnected,
      error: error ?? this.error,
    );
  }
}

// Provider quản lý Service
final chatServiceProvider = Provider((ref) => ChatService());

// StateNotifier quản lý Chat
class ChatNotifier extends StateNotifier<ChatState> {
  final ChatService _chatService;

  ChatNotifier(this._chatService) : super(ChatState(messages: [])) {
    _init();
  }

  void _init() {
    _chatService.connect(1); // Mặc định User ID là 1
    
    // Theo dõi tin nhắn
    _chatService.messages.listen((data) {
      print('DEBUG: Received from WebSocket: $data');
      try {
        // Cập nhật trạng thái connected khi nhận được dữ liệu đầu tiên
        if (!state.isConnected) {
          state = state.copyWith(isConnected: true, error: null);
        }

        final decoded = jsonDecode(data);
        final type = decoded['type'];
        
        if (type == 'delta') {
          final content = decoded['content'] ?? "";
          final messages = [...state.messages];
          
          if (messages.isNotEmpty && messages.last.isAI && messages.last.grammarNotes == null) {
            final last = messages.last;
            messages[messages.length - 1] = ChatMessage(
              content: last.content + content,
              isAI: true,
            );
          } else {
            messages.add(ChatMessage(content: content, isAI: true));
          }
          state = state.copyWith(messages: messages);
        } else if (type == 'completion') {
          print('DEBUG: Received completion with grammar notes');
          final messages = [...state.messages];
          if (messages.isNotEmpty && messages.last.isAI) {
            messages[messages.length - 1] = ChatMessage(
              content: decoded['content'] ?? messages.last.content,
              isAI: true,
              grammarNotes: decoded['grammar_notes'],
            );
          }
          state = state.copyWith(messages: messages);
        } else if (decoded['error'] != null) {
          String errorMsg = decoded['error'];
          print('DEBUG: Received error from WebSocket: $errorMsg');
          
          if (errorMsg.contains('429') || errorMsg.toLowerCase().contains('quota')) {
            errorMsg = "Xin lỗi, hiện tại Robot đang bận (Hết lượt dùng API). Vui lòng thử lại sau vài phút hoặc kiểm tra lại API Key.";
          }
          
          state = state.copyWith(
            messages: [...state.messages, ChatMessage(content: "Error: $errorMsg", isAI: true)],
            error: errorMsg,
          );
        }

      } catch (e) {
        print('DEBUG: Error decoding WebSocket data: $e');
      }
    }, onError: (err) {
      print('DEBUG: WebSocket Stream Error: $err');
      state = state.copyWith(isConnected: false, error: err.toString());
    }, onDone: () {
      print('DEBUG: WebSocket Stream Done');
      state = state.copyWith(isConnected: false);
    });
  }

  void send(String text) {
    if (text.trim().isEmpty) return;
    
    final userMessage = ChatMessage(content: text, isAI: false);
    state = state.copyWith(messages: [...state.messages, userMessage]);
    _chatService.sendMessage(text);
  }

  @override
  void dispose() {
    _chatService.disconnect();
    super.dispose();
  }
}

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>((ref) {
  return ChatNotifier(ref.watch(chatServiceProvider));
});

