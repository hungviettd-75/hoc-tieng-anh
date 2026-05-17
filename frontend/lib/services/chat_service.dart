import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class ChatService {
  WebSocketChannel? _channel;
  WebSocketChannel? _realtimeChannel;

  void connect(int userId) {
    // Sử dụng localhost để tương thích với trình duyệt
    const String ipAddress = '127.0.0.1'; 
    final url = Uri.parse('ws://$ipAddress:8000/api/v1/ws/$userId');

    print('Connecting to WebSocket: $url');
    _channel = WebSocketChannel.connect(url);
  }

  void connectRealtime(int userId) {
    const String ipAddress = '127.0.0.1'; 
    final url = Uri.parse('ws://$ipAddress:8000/api/v1/ws/realtime/$userId');

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
