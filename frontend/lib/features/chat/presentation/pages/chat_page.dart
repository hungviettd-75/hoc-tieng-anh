import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../providers/chat_provider.dart';

class ChatPage extends ConsumerStatefulWidget {
  const ChatPage({super.key});

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final messages = ref.watch(chatProvider);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('AI Coach', style: TextStyle(fontSize: 18)),
            _buildConnectionStatus(messages.isConnected, messages.error),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.mic, color: AppColors.primary),
            onPressed: () => context.push('/voice-chat'),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(20),
              itemCount: messages.messages.length,
              itemBuilder: (context, index) {
                final msg = messages.messages[index];
                return _buildMessage(msg);
              },
            ),
          ),

          _buildInputArea(),
        ],
      ),
    );
  }

  Widget _buildMessage(ChatMessage msg) {
    return Align(
      alignment: msg.isAI ? Alignment.centerLeft : Alignment.centerRight,
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(16),
        constraints: const BoxConstraints(maxWidth: 300),
        decoration: BoxDecoration(
          color: msg.isAI ? AppColors.surface : AppColors.primary.withOpacity(0.2),
          borderRadius: BorderRadius.circular(20),
          border: msg.isAI ? null : Border.all(color: AppColors.primary.withOpacity(0.5)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Expanded(child: SelectableText(msg.content, style: const TextStyle(fontSize: 16))),
                IconButton(
                  icon: const Icon(Icons.copy_rounded, size: 16, color: AppColors.textSecondary),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: msg.content));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Đã sao chép vào bộ nhớ tạm!'), duration: Duration(seconds: 1)),
                    );
                  },
                ),
              ],
            ),
            if (msg.grammarNotes != null && msg.grammarNotes!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8.0),
                child: SelectableText(
                  '💡 ${msg.grammarNotes}',
                  style: const TextStyle(fontSize: 12, color: Colors.amberAccent, fontStyle: FontStyle.italic),
                ),
              ),
          ],
        ),
      ),
    );
  }


  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      decoration: const BoxDecoration(color: AppColors.background),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              decoration: InputDecoration(
                hintText: 'Nhập nội dung tin nhắn...',
                filled: true,
                fillColor: AppColors.surface,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(30), borderSide: BorderSide.none),
              ),
              onSubmitted: (val) => _handleSend(),
            ),
          ),
          const SizedBox(width: 12),
          CircleAvatar(
            backgroundColor: AppColors.primary,
            child: IconButton(
              icon: const Icon(Icons.send, color: Colors.white),
              onPressed: _handleSend,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConnectionStatus(bool isConnected, String? error) {
    if (error != null) {
      return Text('• Lỗi: $error', style: const TextStyle(fontSize: 12, color: Colors.redAccent));
    }
    return Text(
      isConnected ? '• Đã kết nối' : '• Đang kết nối...',
      style: TextStyle(fontSize: 12, color: isConnected ? Colors.greenAccent : Colors.orangeAccent),
    );
  }

  void _handleSend() {
    if (_controller.text.isNotEmpty) {
      ref.read(chatProvider.notifier).send(_controller.text);
      _controller.clear();
      _scrollToBottom();
    }
  }
}
