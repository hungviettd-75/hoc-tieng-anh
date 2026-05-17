import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:animate_do/animate_do.dart';
import 'package:loading_animation_widget/loading_animation_widget.dart';
import 'package:ai_english_coach/services/web_speech_recognizer.dart';
import '../providers/realtime_chat_provider.dart';
import '../widgets/realtime_correction_widget.dart';
import 'package:ai_english_coach/features/learn/presentation/providers/learn_provider.dart';

class VoiceConversationPage extends ConsumerStatefulWidget {
  final String? mode;
  final String? level;

  const VoiceConversationPage({
    super.key,
    this.mode,
    this.level,
  });

  @override
  ConsumerState<VoiceConversationPage> createState() => _VoiceConversationPageState();
}

class _VoiceConversationPageState extends ConsumerState<VoiceConversationPage> with SingleTickerProviderStateMixin {
  bool _isListening = false;
  String _lastWords = '';
  late AnimationController _pulseController;
  
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
  }

  @override
  void dispose() {
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
        ref.read(realtimeChatProvider.notifier).sendVoiceMessage(_lastWords);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(realtimeChatProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close, color: Colors.white),
          onPressed: () {
            ref.invalidate(learningDashboardProvider);
            Navigator.of(context).pop();
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

          // Ô phụ đề
          Positioned(
            bottom: 200,
            left: 20,
            right: 20,
            child: FadeInUp(
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.6),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: Colors.white10),
                ),
                child: Text(
                  _isListening
                      ? (_lastWords.isEmpty ? '🎤 Listening...' : _lastWords)
                      : (state.currentSubtitle.isEmpty
                          ? (state.status == AIStatus.thinking ? '🤔 AI is thinking...' : '👋 Tap mic to talk')
                          : state.currentSubtitle),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, fontSize: 18),
                ),
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
                    _buildIconButton(Icons.mic_off, Colors.white10, () {}),
                    _buildMainVoiceButton(),
                    _buildIconButton(Icons.volume_up, Colors.white10, () {}),
                  ],
                ),
              ],
            ),
          ),

          // Grammar / Pronunciation correction popup
          if (state.currentCorrections.isNotEmpty)
            Positioned(
              top: 100, left: 10, right: 10,
              child: RealtimeCorrectionWidget(
                corrections: state.currentCorrections,
                formattedText: state.formattedCorrectionText,
              ),
            )
          else if (state.lastGrammarCorrection != null && state.lastGrammarCorrection != 'Perfect!' && state.lastGrammarCorrection!.isNotEmpty)
            Positioned(
              top: 100, left: 30, right: 30,
              child: FadeInDown(
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.amberAccent,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [BoxShadow(color: Colors.black45, blurRadius: 10)],
                  ),
                  child: Text(
                    '💡 ${state.lastGrammarCorrection}',
                    style: const TextStyle(color: Colors.black, fontWeight: FontWeight.w600),
                  ),
                ),
              ),
            ),
              ],
            ),
          ),
        ],
      ),
    );
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

  Widget _buildIconButton(IconData icon, Color color, VoidCallback onTap) {
    return IconButton(
      icon: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(shape: BoxShape.circle, color: color),
        child: Icon(icon, color: Colors.white, size: 28),
      ),
      onPressed: onTap,
    );
  }

  Widget _buildTargetKeywordsBanner() {
    final Map<String, List<String>> vocabMap = {
      'A1': ['Beginner', 'Practice', 'Vocabulary', 'Improve'],
      'A2': ['Journey', 'Confident', 'Habit', 'Encourage'],
      'B1': ['Persistent', 'Collaborate', 'Effective', 'Challenge'],
      'B2': ['Substantial', 'Fluency', 'Analyze', 'Evaluate'],
      'C1': ['Pragmatic', 'Eloquent', 'Cognitive', 'Sophisticated'],
    };

    final levelKey = widget.level?.toUpperCase() ?? 'B1';
    final keywords = vocabMap[levelKey] ?? vocabMap['B1']!;
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
}
