import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../providers/chat_provider.dart';
import 'package:ai_english_coach/features/learn/presentation/providers/learn_provider.dart';

class ChatPage extends ConsumerStatefulWidget {
  final String? mode;
  final String? level;
  final String? topic;
  final String? words;

  const ChatPage({
    super.key,
    this.mode,
    this.level,
    this.topic,
    this.words,
  });

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(chatProvider.notifier).connectWithContext(
        mode: widget.mode,
        level: widget.level,
        topic: widget.topic,
        words: widget.words,
      );
    });
  }

  @override
  void dispose() {
    ref.invalidate(learningDashboardProvider);
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

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
      ),
      body: Column(
        children: [
          if (widget.mode == 'vocabulary_practice' && widget.level != null)
            _buildTargetKeywordsBanner(messages.messages),
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
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      decoration: const BoxDecoration(
        color: AppColors.background,
        border: Border(top: BorderSide(color: Colors.white10, width: 0.5)),
      ),
      child: Row(
        children: [
          // Nút Mic đàm thoại với AI Coach - Vị trí nổi bật, dễ nhìn thấy nhất
          GestureDetector(
            onTap: () {
              final topicParam = widget.topic != null ? '&topic=${Uri.encodeComponent(widget.topic!)}' : '';
              final wordsParam = widget.words != null ? '&words=${Uri.encodeComponent(widget.words!)}' : '';
              context.push('/voice-chat?mode=${widget.mode}&level=${widget.level}$topicParam$wordsParam');
            },
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                gradient: AppColors.primaryGradient,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: AppColors.primary.withOpacity(0.4),
                    blurRadius: 10,
                    spreadRadius: 1,
                  ),
                ],
              ),
              child: const Icon(Icons.mic_rounded, color: Colors.white, size: 24),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: TextField(
              controller: _controller,
              style: const TextStyle(color: AppColors.textPrimary),
              decoration: InputDecoration(
                hintText: 'Chạm Mic để nói hoặc nhập tin nhắn...',
                hintStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
                filled: true,
                fillColor: AppColors.surface,
                contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(30), borderSide: BorderSide.none),
              ),
              onSubmitted: (val) => _handleSend(),
            ),
          ),
          const SizedBox(width: 12),
          CircleAvatar(
            radius: 22,
            backgroundColor: AppColors.surface,
            child: IconButton(
              icon: const Icon(Icons.send_rounded, color: AppColors.primary, size: 20),
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

  Widget _buildTargetKeywordsBanner(List<ChatMessage> messageList) {
    final List<String> keywords;
    if (widget.words != null && widget.words!.isNotEmpty) {
      keywords = widget.words!.split(',').map((w) => w.trim()).toList();
    } else {
      final Map<String, List<String>> vocabMap = {
        'A1': ['Beginner', 'Practice', 'Vocabulary', 'Improve'],
        'A2': ['Journey', 'Confident', 'Habit', 'Encourage'],
        'B1': ['Persistent', 'Collaborate', 'Effective', 'Challenge'],
        'B2': ['Substantial', 'Fluency', 'Analyze', 'Evaluate'],
        'C1': ['Pragmatic', 'Eloquent', 'Cognitive', 'Sophisticated'],
      };
      final levelKey = widget.level?.toUpperCase() ?? 'B1';
      keywords = vocabMap[levelKey] ?? vocabMap['B1']!;
    }

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(20, 10, 20, 0),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.primary.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '🎯 Từ vựng mục tiêu cần nói:',
            style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 10,
            runSpacing: 8,
            children: keywords.map((word) {
              // Kiểm tra xem học viên đã từng gõ từ khóa này chưa trong lịch sử chat
              final isSpoken = messageList.any((msg) =>
                  !msg.isAI && msg.content.toLowerCase().contains(word.toLowerCase()));
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: isSpoken ? Colors.green.withOpacity(0.2) : Colors.black26,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isSpoken ? Colors.green : Colors.white24,
                    width: 1,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      isSpoken ? Icons.check_circle_outline_rounded : Icons.radio_button_unchecked_rounded,
                      color: isSpoken ? Colors.green : Colors.white54,
                      size: 14,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      word,
                      style: TextStyle(
                        color: isSpoken ? Colors.greenAccent : Colors.white70,
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
