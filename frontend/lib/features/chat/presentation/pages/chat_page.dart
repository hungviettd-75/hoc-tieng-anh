import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import '../providers/chat_provider.dart';
import 'package:ai_english_coach/features/learn/presentation/providers/learn_provider.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:ai_english_coach/core/api_config.dart';

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
  final AudioPlayer _audioPlayer = AudioPlayer();
  String? _currentlyPlayingMessage;

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
    _audioPlayer.stop();
    _audioPlayer.dispose();
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
    ref.listen<ChatState>(chatProvider, (previous, next) {
      if (next.messages.isNotEmpty) {
        final lastMsg = next.messages.last;
        final prevMsg = previous?.messages.isNotEmpty == true ? previous!.messages.last : null;
        
        // Auto-play when the last message is from AI and has just completed streaming
        // (meaning: next.messages.last.grammarNotes is not null, but in previous state it was null or did not exist)
        if (lastMsg.isAI && lastMsg.grammarNotes != null) {
          final wasNotCompletedYet = prevMsg == null || !prevMsg.isAI || prevMsg.grammarNotes == null;
          
          if (wasNotCompletedYet) {
            print("DEBUG: AI message completed. Playing TTS: ${lastMsg.content}");
            _audioPlayer.stop();
            setState(() {
              _currentlyPlayingMessage = lastMsg.content;
            });
            final url = '${ApiConfig.speaking}/tts?text=${Uri.encodeComponent(lastMsg.content)}';
            _audioPlayer.play(UrlSource(url)).catchError((e) {
              print("Autoplay TTS blocked or failed: $e");
              if (mounted) {
                setState(() {
                  _currentlyPlayingMessage = null;
                });
              }
            });
            _audioPlayer.onPlayerComplete.first.then((_) {
              if (mounted && _currentlyPlayingMessage == lastMsg.content) {
                setState(() {
                  _currentlyPlayingMessage = null;
                });
              }
            });
          }
        }
      }
      _scrollToBottom();
    });

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
    final isPlaying = _currentlyPlayingMessage == msg.content;
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
                if (msg.isAI) ...[
                  IconButton(
                    icon: Icon(
                      isPlaying ? Icons.volume_up_rounded : Icons.volume_up_outlined,
                      size: 18,
                      color: isPlaying ? AppColors.primary : AppColors.textSecondary,
                    ),
                    onPressed: () async {
                      if (isPlaying) {
                        await _audioPlayer.stop();
                        setState(() {
                          _currentlyPlayingMessage = null;
                        });
                      } else {
                        try {
                          await _audioPlayer.stop();
                          setState(() {
                            _currentlyPlayingMessage = msg.content;
                          });
                          final url = '${ApiConfig.speaking}/tts?text=${Uri.encodeComponent(msg.content)}';
                          await _audioPlayer.play(UrlSource(url)).catchError((e) {
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('Không thể phát âm thanh: $e. Hãy tương tác với trang trước!')),
                              );
                            }
                          });
                          _audioPlayer.onPlayerComplete.first.then((_) {
                            if (mounted && _currentlyPlayingMessage == msg.content) {
                              setState(() {
                                _currentlyPlayingMessage = null;
                              });
                            }
                          });
                        } catch (e) {
                          print("ERROR playing TTS in ChatPage: $e");
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Lỗi: $e')),
                            );
                            setState(() {
                              _currentlyPlayingMessage = null;
                            });
                          }
                        }
                      }
                    },
                  ),
                ],
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
              context.push('/voice-chat?mode=${widget.mode}&level=${widget.level}$topicParam$wordsParam&skipWelcome=true');
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
        'A1': ['Beginner', 'Practice', 'Vocabulary', 'Improve', 'Welcome', 'Language', 'Simple', 'Friend', 'Happy', 'Learn', 'Family', 'Morning', 'School', 'Summer', 'Active'],
        'A2': ['Journey', 'Confident', 'Habit', 'Encourage', 'Positive', 'Healthy', 'Creative', 'Success', 'Goal', 'Experience', 'Patient', 'Support', 'Believe', 'Method', 'Imagine'],
        'B1': ['Persistent', 'Collaborate', 'Effective', 'Challenge', 'Achieve', 'Determine', 'Essential', 'Progress', 'Valuable', 'Optimize', 'Dynamic', 'Strategy', 'Productive', 'Opportunity', 'Flexibly'],
        'B2': ['Substantial', 'Fluency', 'Analyze', 'Evaluate', 'Alternative', 'Consequence', 'Significant', 'Distinguish', 'Innovative', 'Perspective', 'Professional', 'Sustainable', 'Coherent', 'Efficient', 'Implement'],
        'C1': ['Pragmatic', 'Eloquent', 'Cognitive', 'Sophisticated', 'Ambiguous', 'Comprehensive', 'Ephemeral', 'Inevitable', 'Paradigm', 'Resilient', 'Ubiquitous', 'Volatile', 'Aesthetic', 'Paradox', 'Synthesis'],
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
