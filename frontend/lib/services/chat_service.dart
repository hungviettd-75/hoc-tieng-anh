import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:ai_english_coach/core/api_config.dart';

class ChatService {
  WebSocketChannel? _channel;
  WebSocketChannel? _realtimeChannel;

  void connect(int userId, {String? mode, String? level, String? topic, String? words}) {
    String urlStr = '${ApiConfig.wsUrl}/ws/$userId';
    final List<String> params = [];
    if (mode != null) params.add('mode=$mode');
    if (level != null) params.add('level=$level');
    if (topic != null) params.add('topic=${Uri.encodeComponent(topic)}');
    if (words != null) params.add('words=${Uri.encodeComponent(words)}');

    if (params.isNotEmpty) {
      urlStr += '?${params.join('&')}';
    }
    final url = Uri.parse(urlStr);

    print('Connecting to WebSocket: $url');
    _channel = WebSocketChannel.connect(url);
  }

  void connectRealtime(int userId, {String? mode, String? level, String? topic, String? words}) {
    String urlStr = '${ApiConfig.wsUrl}/ws/realtime/$userId';
    final List<String> params = [];
    if (mode != null) params.add('mode=$mode');
    if (level != null) params.add('level=$level');
    if (topic != null) params.add('topic=${Uri.encodeComponent(topic)}');
    if (words != null) params.add('words=${Uri.encodeComponent(words)}');

    if (params.isNotEmpty) {
      urlStr += '?${params.join('&')}';
    }
    final url = Uri.parse(urlStr);

    print('Connecting to Realtime WebSocket: $url');
    _realtimeChannel = WebSocketChannel.connect(url);
  }

  Stream<dynamic> get messages => _channel?.stream ?? const Stream.empty();
  Stream<dynamic> get realtimeMessages => _realtimeChannel?.stream ?? const Stream.empty();

  void sendMessage(String content) {
    print('DEBUG: Sending message via WebSocket: $content');
    if (_channel != null) {
      final data = jsonEncode({"content": content});
      _channel!.sink.add(data);
    } else {
      print('DEBUG: WebSocket channel is NULL, cannot send message.');
    }
  }


  void sendRealtimeAction(Map<String, dynamic> action) {
    if (_realtimeChannel != null) {
      _realtimeChannel!.sink.add(jsonEncode(action));
    }
  }

  void disconnect() {
    _channel?.sink.close();
    _realtimeChannel?.sink.close();
  }
}
