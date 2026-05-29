import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:animate_do/animate_do.dart';
import 'package:loading_animation_widget/loading_animation_widget.dart';
import 'package:ai_english_coach/services/web_speech_recognizer.dart';
import '../providers/chat_provider.dart';
import '../providers/realtime_chat_provider.dart';
import '../widgets/realtime_correction_widget.dart';
import 'package:ai_english_coach/features/learn/presentation/providers/learn_provider.dart';

class VoiceConversationPage extends ConsumerStatefulWidget {
  final String? mode;
  final String? level;
  final String? topic;
  final String? words;
  final bool skipWelcome;

  const VoiceConversationPage({
    super.key,
    this.mode,
    this.level,
    this.topic,
    this.words,
    this.skipWelcome = false,
  });

  @override
  ConsumerState<VoiceConversationPage> createState() => _VoiceConversationPageState();
}

class _VoiceConversationPageState extends ConsumerState<VoiceConversationPage> with SingleTickerProviderStateMixin {
  bool _isListening = false;
  bool _isSaving = false;
  String _lastWords = '';
  late AnimationController _pulseController;
  
  // Failsafe mechanism for pronunciation practice to avoid soft-locking users
  int _attemptsCount = 0;
  String? _lastAttemptedWord;
  
  // Web Speech Recognition (native browser API)
  WebSpeechRecognizer? _webSpeech;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    
    if (kIsWeb) {
      _webSpeech = WebSpeechRecognizer();
      _webSpeech!.initialize().then((ok) {
        print('DEBUG: Web Speech init result: $ok');
      });
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(realtimeChatProvider.notifier).connectWithContext(
        mode: widget.mode,
        level: widget.level,
        topic: widget.topic,
        words: widget.words,
        skipWelcome: widget.skipWelcome,
      );
    });
  }

  @override
  void dispose() {
    ref.read(realtimeChatProvider.notifier).resetAndDisconnect();
    _webSpeech?.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  void _listen() {
    print('DEBUG: Mic clicked. isListening=$_isListening');
    
    if (!_isListening) {
      // Bắt đầu nghe
      setState(() {
        _isListening = true;
        _lastWords = '';
      });
      
      if (kIsWeb && _webSpeech != null) {
        String accumulatedText = '';
        _webSpeech!.onResult = (text) {
          if (mounted) {
            setState(() {
              _lastWords = accumulatedText + text;
            });
          }
        };
        _webSpeech!.onEnd = () {
          if (mounted && _isListening) {
            print('DEBUG: Mic timed out, auto-restarting...');
            accumulatedText = _lastWords + ( _lastWords.isNotEmpty ? ' ' : '');
            _webSpeech!.start(locale: 'en-US');
          }
        };
        _webSpeech!.onStatus = (status) {
          if (status.startsWith('error:')) {
            print('DEBUG: Mic Error: $status');
          }
        };
        _webSpeech!.start(locale: 'en-US');
      }
    } else {
      // Dừng nghe và gửi tin nhắn
      setState(() => _isListening = false);
      _webSpeech?.stop();
      
      if (_lastWords.isNotEmpty) {
        print('DEBUG: Sending to AI: "$_lastWords"');
        
        // === Áp dụng Phương án B: So sánh text nghiêm ngặt ===
        if (widget.mode == 'vocabulary_practice') {
          // Lấy danh sách keywords
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
          
          final state = ref.read(realtimeChatProvider);
          final targetWord = _getTargetWord(keywords, state.messages);
          
          if (targetWord != null) {
            // Chuẩn hóa và loại bỏ dấu câu để so sánh chính xác hơn
            final normalizedLastWords = _lastWords.toLowerCase().replaceAll(RegExp(r'[.,\/#!$%\^&\*;:{}=\-_`~()?¿¡"“’“”’]'), ' ').trim();
            final normalizedTargetWord = targetWord.toLowerCase().trim();
            
            if (!normalizedLastWords.contains(normalizedTargetWord)) {
              print('DEBUG: Pronunciation mismatch. User said: "$_lastWords", Target was: "$targetWord"');
              
              // Cảnh báo trên màn hình
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Phát âm chưa chính xác. Từ mục tiêu là: "$targetWord". Vui lòng thử lại!'),
                  backgroundColor: Colors.redAccent,
                  behavior: SnackBarBehavior.floating,
                  duration: const Duration(seconds: 4),
                ),
              );
              
              // Phát cảnh báo bằng giọng nói TTS
              final warningText = 'Từ bạn vừa phát âm chưa chính xác. Từ mục tiêu là "$targetWord". Bạn hãy thử nói lại nhé!';
              ref.read(realtimeChatProvider.notifier).speakWarning(warningText);
              return;
            }
          }
        }
        
        ref.read(realtimeChatProvider.notifier).sendVoiceMessage(_lastWords);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(realtimeChatProvider);

    ref.listen<RealtimeChatState>(realtimeChatProvider, (previous, next) {
      // Tự động ngắt mic khi AI bắt đầu phát âm TTS để tránh vọng/nhiễu
      if (next.isTtsSpeaking && _isListening) {
        setState(() {
          _isListening = false;
        });
        _webSpeech?.stop();
      }
    });

    final scaffold = Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close, color: Colors.white),
          onPressed: () {
            if (widget.mode == 'roleplay') {
              ref.read(realtimeChatProvider.notifier).stopSpeaking(); // Tạm dừng phát âm thanh ngay lập tức
              _showEndSessionConfirmation(context);
            } else {
              // Dừng AI hoàn toàn trước khi thoát chế độ giao tiếp/từ vựng
              ref.read(realtimeChatProvider.notifier).resetAndDisconnect();
              ref.invalidate(learningDashboardProvider);
              Navigator.of(context).pop();
            }
          },
        ),
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8, height: 8,
              decoration: BoxDecoration(
                color: state.status == AIStatus.idle ? Colors.greenAccent : Colors.orangeAccent,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 8),
            const Text('AI English Coach', style: TextStyle(fontSize: 16, color: Colors.white)),
          ],
        ),
      ),
      body: Column(
        children: [
          if (widget.mode == 'vocabulary_practice' && widget.level != null)
            _buildTargetKeywordsBanner(),
          Expanded(
            child: Stack(
              children: [
          // AI Avatar ở giữa
          Center(child: _buildAIAvatar(state.status)),

          // Ô phụ đề song hành (Dual-Subtitle Layout) không che khuất câu hỏi của AI
          Positioned(
            bottom: 200,
            left: 20,
            right: 20,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.85),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: Colors.white12),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.3),
                    blurRadius: 15,
                    offset: const Offset(0, 5),
                  )
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // 1. Phụ đề của AI Coach - Luôn hiển thị để học viên nhìn làm điểm tựa giao tiếp
                  Text(
                    state.currentSubtitle.isEmpty
                        ? (state.status == AIStatus.thinking ? '🤔 AI đang suy nghĩ...' : '👋 Hãy nhấn Mic để bắt đầu trò chuyện!')
                        : state.currentSubtitle,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white, 
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                      height: 1.4,
                    ),
                  ),
                  
                  // 2. Nội dung nhận diện giọng nói của Học viên (Chỉ hiển thị khi đang ghi âm)
                  if (_isListening) ...[
                    const SizedBox(height: 14),
                    Container(
                      width: double.infinity,
                      height: 1,
                      color: Colors.white10,
                    ),
                    const SizedBox(height: 14),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.mic_rounded, color: Colors.greenAccent, size: 16),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _lastWords.isEmpty ? 'Đang lắng nghe... Hãy nói tiếng Anh!' : _lastWords,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.greenAccent, 
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              fontStyle: FontStyle.italic,
                              height: 1.3,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),

          // Nút điều khiển
          Positioned(
            bottom: 40,
            left: 0,
            right: 0,
            child: Column(
              children: [
                if (_isListening)
                  FadeIn(
                    child: const Icon(Icons.waves, color: AppColors.primary, size: 40),
                  ),
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    if (widget.mode == 'roleplay')
                      _buildIconButton(
                        Icons.stop_circle_rounded,
                        Colors.redAccent.withOpacity(0.2),
                        () {
                          ref.read(realtimeChatProvider.notifier).stopSpeaking(); // Tạm dừng phát âm thanh ngay lập tức
                          _showEndSessionConfirmation(context);
                        },
                        tooltip: 'Kết thúc buổi học',
                      )
                    else
                      _buildIconButton(Icons.mic_off, Colors.white10, () {}),
                    _buildMainVoiceButton(),
                    _buildIconButton(Icons.volume_up, Colors.white10, () {}),
                  ],
                ),
              ],
            ),
          ),

          // Grammar / Pronunciation correction popup - ĐÃ LOẠI BỎ THEO YÊU CẦU NGƯỜI DÙNG
              ],
            ),
          ),
        ],
      ),
    );

    if (_isSaving) {
      return Stack(
        children: [
          scaffold,
          Container(
            color: Colors.black.withOpacity(0.75),
            child: Center(
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    LoadingAnimationWidget.staggeredDotsWave(color: AppColors.primary, size: 50),
                    const SizedBox(height: 16),
                    const Text(
                      'Đang tổng hợp báo cáo kết quả...', 
                      style: TextStyle(color: Colors.white, fontSize: 15, decoration: TextDecoration.none, fontWeight: FontWeight.normal),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      );
    }

    return scaffold;
  }

  Widget _buildAIAvatar(AIStatus status) {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        double scale = 1.0 + (_pulseController.value * (status == AIStatus.speaking ? 0.3 : 0.1));
        return Transform.scale(
          scale: scale,
          child: Container(
            width: 140, height: 140,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.primary,
              boxShadow: [BoxShadow(color: AppColors.primary, blurRadius: 40, spreadRadius: 5)],
            ),
            child: status == AIStatus.thinking
                ? LoadingAnimationWidget.staggeredDotsWave(color: Colors.white, size: 50)
                : const Icon(Icons.graphic_eq, color: Colors.white, size: 60),
          ),
        );
      },
    );
  }

  Widget _buildMainVoiceButton() {
    return GestureDetector(
      onTap: _listen,
      child: Container(
        width: 80, height: 80,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: _isListening ? Colors.redAccent : AppColors.primary,
          boxShadow: [BoxShadow(color: (_isListening ? Colors.redAccent : AppColors.primary).withOpacity(0.3), blurRadius: 20)],
        ),
        child: Icon(_isListening ? Icons.stop : Icons.mic, color: Colors.white, size: 40),
      ),
    );
  }

  Widget _buildIconButton(IconData icon, Color color, VoidCallback onTap, {String? tooltip}) {
    final button = IconButton(
      icon: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(shape: BoxShape.circle, color: color),
        child: Icon(icon, color: Colors.white, size: 28),
      ),
      onPressed: onTap,
    );
    
    if (tooltip != null) {
      return Tooltip(message: tooltip, child: button);
    }
    return button;
  }

  Widget _buildTargetKeywordsBanner() {
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
    final state = ref.watch(realtimeChatProvider);

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.surface.withOpacity(0.8),
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
              final isSpoken = _lastWords.toLowerCase().contains(word.toLowerCase()) ||
                  state.currentSubtitle.toLowerCase().contains(word.toLowerCase());
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

  String? _getTargetWord(List<String> keywords, List<ChatMessage> messages) {
    final userTexts = messages
        .where((m) => !m.isAI)
        .map((m) => m.content.toLowerCase())
        .toList();

    for (final word in keywords) {
      final normalizedWord = word.toLowerCase().trim();
      bool isSpoken = false;
      for (final text in userTexts) {
        if (text.contains(normalizedWord)) {
          isSpoken = true;
          break;
        }
      }
      if (!isSpoken) {
        return word;
      }
    }
    return null;
  }

  void _showEndSessionConfirmation(BuildContext context) {
    final pageContext = context; // Lưu context gốc của page
    showDialog(
      context: pageContext,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Kết thúc buổi học?', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        content: const Text(
          'Bạn có chắc chắn muốn kết thúc buổi luyện tập Nhập vai này không? Hệ thống sẽ lưu lại toàn bộ tiến trình của bạn.',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () {
              // Reset flag _stopped để AI có thể tiếp tục nói nếu user không muốn thoát
              ref.read(realtimeChatProvider.notifier).resumeAfterCancel();
              Navigator.pop(dialogContext);
            },
            child: const Text('Hủy', style: TextStyle(color: Colors.white54)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.redAccent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: () async {
              Navigator.pop(dialogContext); // Đóng Dialog xác nhận
              
              // Ngắt kết nối WebSocket và dập tắt âm thanh AI ngay lập tức
              ref.read(realtimeChatProvider.notifier).resetAndDisconnect();
              
              if (mounted) {
                setState(() {
                  _isSaving = true;
                });
              }
              
              // Gọi API lưu phiên học
              final topic = widget.topic ?? 'Nhập vai';
              final level = widget.level ?? 'B1';
              final report = await ref.read(realtimeChatProvider.notifier).endRoleplaySession(topic, level);
              
              if (mounted) {
                setState(() {
                  _isSaving = false;
                });
              }
              
              if (report != null && mounted) {
                _showSessionReport(pageContext, report);
              }
            },
            child: const Text('Kết thúc & Lưu', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Future<void> _showSessionReport(BuildContext context, Map<String, dynamic> report) async {
    final state = ref.read(realtimeChatProvider);
    final pageContext = context; // Lưu context gốc của page
    
    await showModalBottomSheet(
      context: pageContext,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withOpacity(0.85),
      builder: (sheetContext) => DraggableScrollableSheet(
        initialChildSize: 0.9,
        maxChildSize: 0.95,
        minChildSize: 0.6,
        builder: (context, scrollController) => Container(
          decoration: BoxDecoration(
            color: AppColors.background.withOpacity(0.98),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
            border: Border.all(color: Colors.white10),
          ),
          child: Stack(
            children: [
              ListView(
                controller: scrollController,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
                children: [
                  // Header ăn mừng
                  Center(
                    child: Column(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: Colors.greenAccent.withOpacity(0.1),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.emoji_events_rounded, color: Colors.greenAccent, size: 64),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Buổi học hoàn tất! 🎉',
                          style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Bạn đã hoàn thành xuất sắc chủ đề nhập vai: ${widget.topic ?? 'Nhập vai'}',
                          style: const TextStyle(color: Colors.white70, fontSize: 14),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 32),
                  
                  // Khu vực XP và Quà tặng
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [AppColors.primary.withOpacity(0.2), Colors.purpleAccent.withOpacity(0.15)],
                      ),
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: AppColors.primary.withOpacity(0.3)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        Column(
                          children: [
                            const Text('XP Nhận được', style: TextStyle(color: Colors.white70, fontSize: 13)),
                            const SizedBox(height: 6),
                            Text(
                              '+${report['xp_earned']} XP',
                              style: const TextStyle(color: Colors.amber, fontSize: 22, fontWeight: FontWeight.w800),
                            ),
                          ],
                        ),
                        Container(width: 1, height: 40, color: Colors.white24),
                        Column(
                          children: [
                            const Text('Trình độ hiện tại', style: TextStyle(color: Colors.white70, fontSize: 13)),
                            const SizedBox(height: 6),
                            Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  'Level ${report['level']}',
                                  style: const TextStyle(color: Colors.greenAccent, fontSize: 22, fontWeight: FontWeight.w800),
                                ),
                                if (report['leveled_up'] == true) ...[
                                  const SizedBox(width: 6),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: Colors.redAccent,
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: const Text('UP!', style: TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold)),
                                  )
                                ]
                              ],
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 28),
                  
                  // Điểm số Metrics
                  const Text(
                    '📊 Chỉ số kỹ năng của bạn',
                    style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  _buildScoreProgressBar('Phát âm (Pronunciation)', report['pronunciation_score'], Colors.blueAccent),
                  const SizedBox(height: 12),
                  _buildScoreProgressBar('Độ lưu loát (Fluency)', report['fluency_score'], Colors.greenAccent),
                  const SizedBox(height: 12),
                  _buildScoreProgressBar('Sự tự tin (Confidence)', report['confidence_score'], Colors.orangeAccent),
                  const SizedBox(height: 28),
                  
                  // Thống kê nhanh Grid
                  const Text(
                    '🎯 Thống kê chi tiết',
                    style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  GridView.count(
                    crossAxisCount: 3,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                    childAspectRatio: 1.1,
                    children: [
                      _buildStatCard('Thời lượng', '${report['duration_minutes']} phút', Icons.timer),
                      _buildStatCard('Số câu nói', '${report['sentence_count']} câu', Icons.chat_bubble_outline),
                      _buildStatCard('Lỗi sai', '${report['pronunciation_errors_count'] + report['grammar_errors_count']} lỗi', Icons.warning_amber),
                    ],
                  ),
                  const SizedBox(height: 28),
                  
                  // Danh sách lỗi sai đã sửa (Mistakes Review)
                  if (state.allSessionMistakes.isNotEmpty) ...[
                    const Text(
                      '💡 Các điểm cần ôn tập lại',
                      style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 16),
                    ...state.allSessionMistakes.map((mistake) => Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppColors.surface,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: Colors.white12),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: mistake.errorType == 'pronunciation' ? Colors.blueAccent.withOpacity(0.2) : Colors.amber.withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  mistake.errorType == 'pronunciation' ? 'Phát âm' : 'Ngữ pháp',
                                  style: TextStyle(
                                    color: mistake.errorType == 'pronunciation' ? Colors.blueAccent : Colors.amber,
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          RichText(
                            text: TextSpan(
                              style: const TextStyle(fontSize: 14, height: 1.3),
                              children: [
                                const TextSpan(text: '❌ Bạn nói: ', style: TextStyle(color: Colors.redAccent)),
                                TextSpan(text: '"${mistake.original}"', style: const TextStyle(color: Colors.white, fontStyle: FontStyle.italic)),
                              ],
                            ),
                          ),
                          const SizedBox(height: 6),
                          RichText(
                            text: TextSpan(
                              style: const TextStyle(fontSize: 14, height: 1.3),
                              children: [
                                const TextSpan(text: '✅ Nên nói: ', style: TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold)),
                                TextSpan(text: '"${mistake.correction}"', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                                if (mistake.ipa.isNotEmpty)
                                  TextSpan(text: '  ${mistake.ipa}', style: const TextStyle(color: Colors.blueAccent, fontSize: 13)),
                              ],
                            ),
                          ),
                          const SizedBox(height: 8),
                          Container(width: double.infinity, height: 1, color: Colors.white10),
                          const SizedBox(height: 8),
                          Text(
                            '💡 ${mistake.explanationVi}',
                            style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.4),
                          ),
                        ],
                      ),
                    )),
                    const SizedBox(height: 16),
                  ],
                  
                  // Nút hoàn tất
                  const SizedBox(height: 16),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      elevation: 5,
                      shadowColor: AppColors.primary.withOpacity(0.4),
                    ),
                    onPressed: () {
                      ref.invalidate(learningDashboardProvider);
                      Navigator.pop(sheetContext); // Chỉ đóng BottomSheet bằng sheetContext
                    },
                    child: const Text(
                      'Hoàn thành & Trở về',
                      style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(height: 32),
                ],
              ),
            ],
          ),
        ),
      ),
    );

    if (mounted) {
      Navigator.of(pageContext).pop(); // Thoát page bằng pageContext gốc sau khi BottomSheet đã đóng
    }
  }

  Widget _buildScoreProgressBar(String title, double score, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(title, style: const TextStyle(color: Colors.white70, fontSize: 13)),
            Text('${score.toStringAsFixed(0)}/100', style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: LinearProgressIndicator(
            value: score / 100.0,
            minHeight: 8,
            backgroundColor: Colors.white10,
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: AppColors.primary, size: 20),
          const SizedBox(height: 8),
          Text(value, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: Colors.white38, fontSize: 9)),
        ],
      ),
    );
  }
}
