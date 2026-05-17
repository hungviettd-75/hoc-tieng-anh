import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:http/http.dart' as http;
import 'package:record/record.dart';
import 'package:ai_english_coach/core/api_config.dart';
import 'package:ai_english_coach/services/speaking_service.dart';
import '../../../speaking/models/pronunciation_models.dart';

/// Provider cho SpeakingService
final speakingServiceProvider = Provider((ref) => SpeakingService());

/// Các phase của quá trình luyện phát âm
enum SpeakingPhase { idle, recording, analyzing, result, error }

/// State cho Speaking feature
class SpeakingState {
  final SpeakingPhase phase;
  final PronunciationResult? result;
  final List<PracticeSentence> sentences;
  final PronunciationHistory? history;
  final String? errorMessage;
  final List<double> amplitudes;
  final Uint8List? lastAudioBytes;

  SpeakingState({
    this.phase = SpeakingPhase.idle,
    this.result,
    this.sentences = const [],
    this.history,
    this.errorMessage,
    this.amplitudes = const [],
    this.lastAudioBytes,
  });

  SpeakingState copyWith({
    SpeakingPhase? phase,
    PronunciationResult? result,
    List<PracticeSentence>? sentences,
    PronunciationHistory? history,
    String? errorMessage,
    List<double>? amplitudes,
    Uint8List? lastAudioBytes,
  }) {
    return SpeakingState(
      phase: phase ?? this.phase,
      result: result ?? this.result,
      sentences: sentences ?? this.sentences,
      history: history ?? this.history,
      errorMessage: errorMessage ?? this.errorMessage,
      amplitudes: amplitudes ?? this.amplitudes,
      lastAudioBytes: lastAudioBytes ?? this.lastAudioBytes,
    );
  }
}

/// StateNotifier quản lý toàn bộ speaking flow
class SpeakingNotifier extends StateNotifier<SpeakingState> {
  final SpeakingService _service;
  final AudioPlayer _audioPlayer = AudioPlayer();
  final AudioRecorder _recorder = AudioRecorder();
  Timer? _amplitudeTimer;

  SpeakingNotifier(this._service) : super(SpeakingState()) {
    loadSentences();
  }

  /// Tải danh sách câu luyện tập
  Future<void> loadSentences({String? level}) async {
    try {
      final sentences = await _service.getSentences(level: level);
      state = state.copyWith(sentences: sentences);
    } catch (e) {
      print('SpeakingNotifier: Failed to load sentences: $e');
    }
  }

  /// Tải lịch sử
  Future<void> loadHistory() async {
    try {
      final history = await _service.getHistory(1);
      state = state.copyWith(history: history);
    } catch (e) {
      print('SpeakingNotifier: Failed to load history: $e');
    }
  }

  /// Phát mẫu target sentence bằng TTS
  Future<void> playReference(String text) async {
    try {
      final url = '${ApiConfig.speaking}/tts?text=${Uri.encodeComponent(text)}';
      await _audioPlayer.play(UrlSource(url));
    } catch (e) {
      print('Error playing audio: $e');
    }
  }

  /// Stop TTS
  Future<void> stopTts() async {
    await _audioPlayer.stop();
  }

  /// Bắt đầu ghi âm
  Future<void> startRecording() async {
    try {
      if (await _recorder.hasPermission()) {
        await _recorder.start(
          const RecordConfig(
            encoder: AudioEncoder.aacLc,
            numChannels: 1,
            sampleRate: 44100,
          ),
          path: '',
        );
        
        state = state.copyWith(
          phase: SpeakingPhase.recording,
          amplitudes: [],
        );

        // Cập nhật amplitude cho waveform animation
        _amplitudeTimer = Timer.periodic(
          const Duration(milliseconds: 100),
          (_) async {
            try {
              final amp = await _recorder.getAmplitude();
              final normalized = ((amp.current + 50).clamp(0, 50)) / 50.0;
              if (mounted) {
                final newAmps = List<double>.from(state.amplitudes)..add(normalized);
                // Giới hạn số lượng amplitudes để tránh memory leak
                if (newAmps.length > 200) newAmps.removeAt(0);
                state = state.copyWith(amplitudes: newAmps);
              }
            } catch (_) {}
          },
        );
      } else {
        state = state.copyWith(
          phase: SpeakingPhase.error,
          errorMessage: 'Microphone permission denied. Vui lòng cấp quyền trong Chrome.',
        );
      }
    } catch (e, stack) {
      print('SpeakingNotifier: Recording error: $e\n$stack');
      state = state.copyWith(
        phase: SpeakingPhase.error,
        errorMessage: 'Cannot start recording: $e',
      );
    }
  }

  /// Dừng ghi âm và gửi phân tích
  Future<void> stopAndAnalyze(String targetText) async {
    _amplitudeTimer?.cancel();
    state = state.copyWith(phase: SpeakingPhase.analyzing);

    try {
      final path = await _recorder.stop();
      if (path == null || path.isEmpty) {
        state = state.copyWith(
          phase: SpeakingPhase.error,
          errorMessage: 'No audio recorded.',
        );
        return;
      }

      Uint8List audioBytes;
      try {
        final response = await http.get(Uri.parse(path));
        audioBytes = response.bodyBytes;
      } catch (e) {
        state = state.copyWith(
          phase: SpeakingPhase.error,
          errorMessage: 'Lỗi khi đọc file ghi âm: $e',
        );
        return;
      }

      if (audioBytes.isEmpty) {
        state = state.copyWith(
          phase: SpeakingPhase.error,
          errorMessage: 'Audio data is empty (kích thước 0 byte).',
        );
        return;
      }

      state = state.copyWith(lastAudioBytes: audioBytes);

      // Gửi tới backend Gemini-powered service
      final result = await _service.analyzePronunciation(
        audioBytes: audioBytes,
        targetText: targetText,
      );

      state = state.copyWith(
        phase: SpeakingPhase.result,
        result: result,
      );
    } catch (e, stack) {
      print('SpeakingNotifier: Analyze error: $e\n$stack');
      state = state.copyWith(
        phase: SpeakingPhase.error,
        errorMessage: 'Lỗi khi gửi lên AI: $e',
      );
    }
  }

  /// Reset state về idle
  void reset() {
    state = SpeakingState(
      sentences: state.sentences,
      history: state.history,
    );
  }

  @override
  void dispose() {
    _amplitudeTimer?.cancel();
    _recorder.dispose();
    _audioPlayer.stop();
    _audioPlayer.dispose();
    super.dispose();
  }
}

/// Provider chính
final speakingProvider = StateNotifierProvider<SpeakingNotifier, SpeakingState>((ref) {
  return SpeakingNotifier(ref.watch(speakingServiceProvider));
});
