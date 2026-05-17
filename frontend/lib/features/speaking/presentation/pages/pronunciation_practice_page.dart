import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:animate_do/animate_do.dart';
import 'package:loading_animation_widget/loading_animation_widget.dart';
import '../../models/pronunciation_models.dart';
import '../providers/speaking_provider.dart';
import '../widgets/waveform_painter.dart';

class PronunciationPracticePage extends ConsumerStatefulWidget {
  final PracticeSentence sentence;
  const PronunciationPracticePage({super.key, required this.sentence});

  @override
  ConsumerState<PronunciationPracticePage> createState() =>
      _PronunciationPracticePageState();
}

class _PronunciationPracticePageState
    extends ConsumerState<PronunciationPracticePage> {
  bool _isPlayingRef = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      if (mounted) {
        ref.read(speakingProvider.notifier).reset();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(speakingProvider);

    ref.listen<SpeakingState>(speakingProvider, (previous, next) {
      if (next.phase == SpeakingPhase.result && next.result != null) {
        context.push('/speaking/result', extra: next.result);
      }
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close, color: Colors.white),
          onPressed: () {
            ref.read(speakingProvider.notifier).reset();
            context.pop();
          },
        ),
        title: Text('Level ${widget.sentence.level}',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 14)),
        centerTitle: true,
      ),
      body: SafeArea(
        child: Column(
          children: [
            const Spacer(flex: 1),
            // Target sentence
            FadeInDown(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Column(children: [
                  const Icon(Icons.format_quote_rounded,
                      color: AppColors.primary, size: 32),
                  const SizedBox(height: 12),
                  Text(widget.sentence.text,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 24,
                          fontWeight: FontWeight.w600,
                          height: 1.4)),
                ]),
              ),
            ),
            const SizedBox(height: 32),
            // Listen button
            FadeInUp(
              delay: const Duration(milliseconds: 200),
              child: GestureDetector(
                onTap: () {
                  setState(() => _isPlayingRef = true);
                  ref.read(speakingProvider.notifier).playReference(widget.sentence.text);
                  Future.delayed(const Duration(seconds: 3),
                      () { if (mounted) setState(() => _isPlayingRef = false); });
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(30),
                    border: Border.all(color: _isPlayingRef
                        ? AppColors.primary.withOpacity(0.5) : Colors.white10),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(_isPlayingRef ? Icons.volume_up_rounded : Icons.headphones_rounded,
                        color: AppColors.primary, size: 20),
                    const SizedBox(width: 8),
                    Text(_isPlayingRef ? 'Playing...' : 'Listen to example',
                        style: const TextStyle(color: AppColors.textPrimary, fontSize: 14)),
                  ]),
                ),
              ),
            ),
            const Spacer(flex: 2),
            // Waveform
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: WaveformWidget(
                amplitudes: state.amplitudes,
                isRecording: state.phase == SpeakingPhase.recording,
                height: 100,
              ),
            ),
            const SizedBox(height: 16),
            _buildStatusText(state.phase),
            const SizedBox(height: 32),
            _buildRecordButton(state),
            const SizedBox(height: 16),
            if (state.phase == SpeakingPhase.idle)
              Text('Tap the mic to start recording',
                  style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
            if (state.phase == SpeakingPhase.error)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Text(state.errorMessage ?? 'Error',
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: AppColors.error, fontSize: 13)),
              ),
            const Spacer(flex: 1),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusText(SpeakingPhase phase) {
    final map = {
      SpeakingPhase.idle: ('Ready to record', AppColors.textSecondary),
      SpeakingPhase.recording: ('🎤 Recording... Tap to stop', Colors.redAccent),
      SpeakingPhase.analyzing: ('🧠 AI is analyzing...', AppColors.primary),
      SpeakingPhase.result: ('✅ Complete!', AppColors.success),
      SpeakingPhase.error: ('❌ Error', AppColors.error),
    };
    final entry = map[phase]!;
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      child: Text(entry.$1, key: ValueKey(phase),
          style: TextStyle(color: entry.$2, fontSize: 15, fontWeight: FontWeight.w500)),
    );
  }

  Widget _buildRecordButton(SpeakingState state) {
    if (state.phase == SpeakingPhase.analyzing) {
      return Container(
        width: 90, height: 90,
        decoration: BoxDecoration(
          shape: BoxShape.circle, color: AppColors.surface,
          border: Border.all(color: AppColors.primary.withOpacity(0.3), width: 3),
        ),
        child: Center(child: LoadingAnimationWidget.staggeredDotsWave(
            color: AppColors.primary, size: 36)),
      );
    }
    final isRec = state.phase == SpeakingPhase.recording;
    return GestureDetector(
      onTap: () {
        if (isRec) {
          ref.read(speakingProvider.notifier).stopAndAnalyze(widget.sentence.text);
        } else {
          ref.read(speakingProvider.notifier).startRecording();
        }
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        width: isRec ? 90 : 80, height: isRec ? 90 : 80,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(colors: isRec
              ? [Colors.redAccent, Colors.red]
              : [AppColors.primary, AppColors.secondary]),
          boxShadow: [BoxShadow(
            color: (isRec ? Colors.redAccent : AppColors.primary).withOpacity(0.4),
            blurRadius: isRec ? 30 : 20, spreadRadius: isRec ? 5 : 0,
          )],
        ),
        child: Icon(isRec ? Icons.stop_rounded : Icons.mic_rounded,
            color: Colors.white, size: isRec ? 40 : 36),
      ),
    );
  }
}
