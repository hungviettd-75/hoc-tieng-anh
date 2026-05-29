import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:animate_do/animate_do.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:ai_english_coach/core/api_config.dart';
import 'package:ai_english_coach/features/auth/services/auth_service.dart';

enum GameMode {
  multipleChoice,
  matchPair,
  speedChallenge,
  audioVocab,
  imageVocab,
  sentenceMatching,
  memoryFlip,
}

class VocabularyMatchingGamePage extends StatefulWidget {
  final String level;

  const VocabularyMatchingGamePage({
    super.key,
    required this.level,
  });

  @override
  State<VocabularyMatchingGamePage> createState() => _VocabularyMatchingGamePageState();
}

class _VocabularyMatchingGamePageState extends State<VocabularyMatchingGamePage> {
  GameMode? _selectedMode;
  bool _isLoading = false;
  String _errorMessage = '';
  List<Question> _questions = [];
  int _currentIndex = 0;
  
  // Trạng thái chơi câu hiện tại (Multiple Choice, Audio, Image, Sentence)
  String? _selectedAnswer;
  bool _hasAnswered = false;
  bool _isAnswerCorrect = false;

  // Trạng thái Match Pair
  List<GameCard> _leftCards = [];
  List<GameCard> _rightCards = [];
  GameCard? _selectedLeft;
  GameCard? _selectedRight;
  int _matchedPairsCount = 0;

  // Trạng thái Memory Flip
  List<MemoryCard> _memoryCards = [];
  int? _firstFlippedIndex;
  int? _secondFlippedIndex;
  bool _isFlippingActive = true;

  // Điểm số & Gamification
  int _score = 0;
  int _xpEarned = 0;
  int _comboStreak = 0;
  int _maxCombo = 0;
  List<Attempt> _attempts = [];

  // Âm thanh & Thời gian
  final AudioPlayer _audioPlayer = AudioPlayer();
  final AudioPlayer _effectPlayer = AudioPlayer();
  Timer? _gameTimer;
  int _secondsElapsed = 0;
  int _speedTimeLeft = 60; // Dành riêng cho Speed Challenge

  @override
  void dispose() {
    _gameTimer?.cancel();
    _audioPlayer.stop();
    _audioPlayer.dispose();
    _effectPlayer.stop();
    _effectPlayer.dispose();
    super.dispose();
  }

  void _startTimer() {
    _gameTimer?.cancel();
    _secondsElapsed = 0;
    _speedTimeLeft = 60;

    _gameTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      
      if (_selectedMode == GameMode.speedChallenge) {
        setState(() {
          if (_speedTimeLeft > 0) {
            _speedTimeLeft--;
          } else {
            _gameTimer?.cancel();
            _finishGame();
          }
        });
      } else {
        setState(() {
          _secondsElapsed++;
        });
      }
    });
  }

  Future<void> _playTts(String text) async {
    try {
      await _audioPlayer.stop();
      final url = '${ApiConfig.speaking}/tts?text=${Uri.encodeComponent(text)}';
      await _audioPlayer.play(UrlSource(url));
    } catch (e) {
      print("Error playing TTS: $e");
    }
  }

  Future<void> _playEffect(bool correct) async {
    try {
      await _effectPlayer.stop();
      final phrase = correct ? "Correct" : "Incorrect";
      final url = '${ApiConfig.speaking}/tts?text=${Uri.encodeComponent(phrase)}';
      await _effectPlayer.play(UrlSource(url));
    } catch (e) {
      print("Error playing sound effect: $e");
    }
  }

  Future<void> _initGame(GameMode mode) async {
    setState(() {
      _selectedMode = mode;
      _isLoading = true;
      _errorMessage = '';
      _questions = [];
      _currentIndex = 0;
      _score = 0;
      _xpEarned = 0;
      _comboStreak = 0;
      _maxCombo = 0;
      _attempts = [];
      _hasAnswered = false;
      _selectedAnswer = null;
      _leftCards = [];
      _rightCards = [];
      _selectedLeft = null;
      _selectedRight = null;
      _matchedPairsCount = 0;
      _memoryCards = [];
      _firstFlippedIndex = null;
      _secondFlippedIndex = null;
      _isFlippingActive = true;
    });

    try {
      final token = await AuthService().getAccessToken();
      final headers = {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

      // Tải bộ câu hỏi từ backend
      final response = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/learn/vocabulary-game/questions?level=${widget.level}'),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data.isEmpty) {
          setState(() {
            _errorMessage = 'Không tìm thấy từ vựng để tạo game.';
            _isLoading = false;
          });
          return;
        }

        final loadedQuestions = data.map((q) => Question.fromJson(q)).toList();

        // Tạo danh sách các phương án tiếng Anh cho mỗi câu hỏi (dùng trong Image Vocab)
        for (var q in loadedQuestions) {
          final Set<String> opts = {q.word};
          final otherWords = loadedQuestions
              .map((e) => e.word)
              .where((w) => w.toLowerCase() != q.word.toLowerCase())
              .toList();
          otherWords.shuffle();
          for (var w in otherWords) {
            if (opts.length >= 4) break;
            opts.add(w);
          }
          while (opts.length < 4) {
            opts.add("Word ${opts.length}");
          }
          final shuffledOpts = opts.toList();
          shuffledOpts.shuffle();
          q.englishOptions = shuffledOpts;
        }

        setState(() {
          _questions = loadedQuestions;
          _isLoading = false;
        });

        // Thiết lập cấu trúc game đặc thù cho từng Mode
        if (mode == GameMode.matchPair || mode == GameMode.speedChallenge) {
          _setupMatchPairs();
        } else if (mode == GameMode.memoryFlip) {
          _setupMemoryFlip();
        }

        _startTimer();

        // Tự động phát âm ở Mode Audio khi bắt đầu câu đầu tiên
        if (mode == GameMode.audioVocab && _questions.isNotEmpty) {
          _playTts(_questions[0].word);
        }
      } else {
        setState(() {
          _errorMessage = 'Lỗi từ server khi tải game.';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Lỗi kết nối. Vui lòng kiểm tra mạng!';
        _isLoading = false;
      });
    }
  }

  // Thiết lập game Match Pairs / Speed Challenge (cặp từ)
  void _setupMatchPairs() {
    _leftCards = [];
    _rightCards = [];
    _matchedPairsCount = 0;

    // Lấy tối đa 5 cặp cho Match Pair
    final playCount = _questions.length > 5 ? 5 : _questions.length;
    for (int i = 0; i < playCount; i++) {
      final q = _questions[i];
      _leftCards.add(GameCard(id: i, text: q.word, isEnglish: true));
      _rightCards.add(GameCard(id: i, text: q.correctAnswer, isEnglish: false));
    }

    _leftCards.shuffle();
    _rightCards.shuffle();
  }

  // Thiết lập game Memory Flip Cards
  void _setupMemoryFlip() {
    _memoryCards = [];
    // Lấy 4 cặp từ để chơi 8 thẻ
    final playCount = _questions.length > 4 ? 4 : _questions.length;
    for (int i = 0; i < playCount; i++) {
      final q = _questions[i];
      _memoryCards.add(MemoryCard(id: i, text: q.word, isEnglish: true));
      _memoryCards.add(MemoryCard(id: i, text: q.correctAnswer, isEnglish: false));
    }
    _memoryCards.shuffle();
  }

  // Submit câu trả lời cho các mode trắc nghiệm (MultipleChoice, AudioVocab, ImageVocab, SentenceMatching)
  void _submitSelection(String answer) {
    if (_hasAnswered) return;

    final currentQuestion = _questions[_currentIndex];
    final isCorrect = (_selectedMode == GameMode.imageVocab || _selectedMode == GameMode.sentenceMatching)
        ? answer.trim().toLowerCase() == currentQuestion.word.trim().toLowerCase()
        : answer.trim().toLowerCase() == currentQuestion.correctAnswer.trim().toLowerCase();

    setState(() {
      _selectedAnswer = answer;
      _hasAnswered = true;
      _isAnswerCorrect = isCorrect;

      if (isCorrect) {
        _comboStreak++;
        if (_comboStreak > _maxCombo) _maxCombo = _comboStreak;
        final comboBonus = (_comboStreak > 1) ? ((_comboStreak - 1) * 2).clamp(0, 10) : 0;
        _score += 10 + comboBonus;
        _xpEarned += 5 + (comboBonus ~/ 2);
      } else {
        _comboStreak = 0;
      }

      _attempts.add(Attempt(
        word: currentQuestion.word,
        userAnswer: answer,
        isCorrect: isCorrect,
      ));
    });

    _playEffect(isCorrect);
    Future.delayed(const Duration(milliseconds: 500), () {
      if (mounted) {
        _playTts("${currentQuestion.word}. ${currentQuestion.example}");
      }
    });
  }

  // Xử lý chạm thẻ ở chế độ Match Pairs
  void _handleMatchPairTap(GameCard card) {
    if (card.isMatched) return;

    setState(() {
      if (card.isEnglish) {
        _selectedLeft = (_selectedLeft == card) ? null : card;
      } else {
        _selectedRight = (_selectedRight == card) ? null : card;
      }
    });

    if (_selectedLeft != null && _selectedRight != null) {
      final left = _selectedLeft!;
      final right = _selectedRight!;

      if (left.id == right.id) {
        setState(() {
          left.isMatched = true;
          right.isMatched = true;
          left.status = CardStatus.correct;
          right.status = CardStatus.correct;
          _score += 10;
          _xpEarned += 5;
          _matchedPairsCount++;
          _selectedLeft = null;
          _selectedRight = null;
        });

        _playEffect(true);

        // Phát âm từ vựng vừa ghép đúng
        _playTts(_questions[left.id].word);

        if (_matchedPairsCount == _leftCards.length) {
          Future.delayed(const Duration(milliseconds: 800), () {
            if (mounted) _finishGame();
          });
        }
      } else {
        setState(() {
          left.status = CardStatus.incorrect;
          right.status = CardStatus.incorrect;
        });
        _playEffect(false);

        final tempLeft = left;
        final tempRight = right;
        _selectedLeft = null;
        _selectedRight = null;

        Future.delayed(const Duration(milliseconds: 600), () {
          if (mounted) {
            setState(() {
              if (tempLeft.status == CardStatus.incorrect) tempLeft.status = CardStatus.normal;
              if (tempRight.status == CardStatus.incorrect) tempRight.status = CardStatus.normal;
            });
          }
        });
      }
    }
  }

  // Xử lý lật thẻ ở chế độ Memory Flip Cards
  void _handleMemoryFlipTap(int index) {
    if (!_isFlippingActive) return;
    final card = _memoryCards[index];
    if (card.isFlipped || card.isMatched) return;

    setState(() {
      card.isFlipped = true;
      if (_firstFlippedIndex == null) {
        _firstFlippedIndex = index;
      } else {
        _secondFlippedIndex = index;
        _isFlippingActive = false;
        _checkMemoryMatch();
      }
    });
  }

  void _checkMemoryMatch() {
    final first = _memoryCards[_firstFlippedIndex!];
    final second = _memoryCards[_secondFlippedIndex!];

    if (first.id == second.id) {
      setState(() {
        first.isMatched = true;
        second.isMatched = true;
        _score += 15;
        _xpEarned += 8;
        _firstFlippedIndex = null;
        _secondFlippedIndex = null;
        _isFlippingActive = true;

        final allMatched = _memoryCards.every((c) => c.isMatched);
        if (allMatched) {
          Future.delayed(const Duration(milliseconds: 600), () {
            if (mounted) _finishGame();
          });
        }
      });
      _playEffect(true);
    } else {
      _playEffect(false);
      Future.delayed(const Duration(milliseconds: 1000), () {
        if (mounted) {
          setState(() {
            first.isFlipped = false;
            second.isFlipped = false;
            _firstFlippedIndex = null;
            _secondFlippedIndex = null;
            _isFlippingActive = true;
          });
        }
      });
    }
  }

  void _nextQuestion() {
    if (_currentIndex < _questions.length - 1) {
      setState(() {
        _currentIndex++;
        _hasAnswered = false;
        _selectedAnswer = null;
      });
      if (_selectedMode == GameMode.audioVocab) {
        _playTts(_questions[_currentIndex].word);
      }
    } else {
      _finishGame();
    }
  }

  Future<void> _finishGame() async {
    _gameTimer?.cancel();
    setState(() {
      _isLoading = true;
    });

    try {
      final token = await AuthService().getAccessToken();
      final headers = {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

      final body = jsonEncode({
        'level': widget.level,
        'score': _score,
        'xp_earned': _xpEarned,
        'duration_seconds': _secondsElapsed,
        'attempts': _attempts.map((a) => a.toJson()).toList(),
      });

      await http.post(
        Uri.parse('${ApiConfig.baseUrl}/learn/vocabulary-game/save-result'),
        headers: headers,
        body: body,
      ).timeout(const Duration(seconds: 10));

    } catch (e) {
      print("Error saving game result: $e");
    }

    setState(() {
      _isLoading = false;
      _currentIndex = _questions.length; // Trạng thái hoàn thành game
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () {
            if (_selectedMode != null) {
              setState(() {
                _selectedMode = null;
                _gameTimer?.cancel();
              });
            } else {
              context.pop();
            }
          },
        ),
        title: Text(
          _selectedMode == null ? 'Trò chơi từ vựng' : 'Đang luyện tập trình độ ${widget.level}',
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
      ),
      body: SafeArea(
        child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
            : _errorMessage.isNotEmpty
                ? _buildErrorState()
                : _selectedMode == null
                    ? _buildModeSelectionMenu()
                    : _currentIndex >= _questions.length
                        ? _buildGameOverState()
                        : _buildGameplayArea(),
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline_rounded, size: 64, color: AppColors.error),
          const SizedBox(height: 16),
          Text(_errorMessage, style: const TextStyle(color: Colors.white70, fontSize: 16)),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: () => _selectedMode != null ? _initGame(_selectedMode!) : context.pop(),
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary),
            child: const Text('Thử lại', style: TextStyle(color: Colors.white)),
          )
        ],
      ),
    );
  }

  // MENU CHỌN 7 MINI GAME
  Widget _buildModeSelectionMenu() {
    final modes = [
      {
        'mode': GameMode.multipleChoice,
        'title': 'Trắc nghiệm nghĩa',
        'desc': 'Chọn nghĩa tiếng Việt đúng cho từ tiếng Anh',
        'icon': Icons.checklist_rtl_rounded,
        'color': AppColors.primary,
      },
      {
        'mode': GameMode.matchPair,
        'title': 'Ghép cặp từ',
        'desc': 'Ghép các từ tiếng Anh với nghĩa tiếng Việt tương ứng',
        'icon': Icons.compare_arrows_rounded,
        'color': AppColors.secondary,
      },
      {
        'mode': GameMode.speedChallenge,
        'title': 'Thử thách tốc độ',
        'desc': 'Ghép càng nhiều từ càng tốt trong 60 giây',
        'icon': Icons.timer_outlined,
        'color': AppColors.tertiary,
      },
      {
        'mode': GameMode.audioVocab,
        'title': 'Luyện nghe phản xạ',
        'desc': 'Nghe AI đọc từ tiếng Anh và chọn nghĩa đúng',
        'icon': Icons.volume_up_rounded,
        'color': Colors.cyan,
      },
      {
        'mode': GameMode.imageVocab,
        'title': 'Từ vựng qua ảnh',
        'desc': 'Xem hình ảnh minh họa sinh động và đoán từ',
        'icon': Icons.image_search_rounded,
        'color': Colors.pinkAccent,
      },
      {
        'mode': GameMode.sentenceMatching,
        'title': 'Ghép câu hoàn chỉnh',
        'desc': 'Tìm nghĩa đúng của câu tiếng Anh',
        'icon': Icons.text_snippet_rounded,
        'color': Colors.teal,
      },
      {
        'mode': GameMode.memoryFlip,
        'title': 'Trí nhớ lật bài',
        'desc': 'Lật tìm các cặp từ và nghĩa trùng khớp',
        'icon': Icons.style_rounded,
        'color': Colors.amber,
      },
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 10),
          FadeInDown(
            child: const Text(
              'Chọn chế độ chơi 🎮',
              style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Chọn một mini game dưới đây để luyện phản xạ từ vựng thật vui và nhận nhiều điểm XP nhé!',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 20),
          Expanded(
            child: ListView.builder(
              itemCount: modes.length,
              itemBuilder: (context, index) {
                final m = modes[index];
                final color = m['color'] as Color;
                return FadeInUp(
                  delay: Duration(milliseconds: 80 * index),
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 14),
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: color.withOpacity(0.15), width: 1.5),
                    ),
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                      leading: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: color.withOpacity(0.15),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(m['icon'] as IconData, color: color, size: 24),
                      ),
                      title: Text(
                        m['title'] as String,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      subtitle: Padding(
                        padding: const EdgeInsets.only(top: 4.0),
                        child: Text(
                          m['desc'] as String,
                          style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                        ),
                      ),
                      trailing: const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white24, size: 16),
                      onTap: () => _initGame(m['mode'] as GameMode),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  // KHU VỰC CHƠI GAME CHÍNH
  Widget _buildGameplayArea() {
    final progress = (_currentIndex + 1) / _questions.length;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Stats Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (_selectedMode == GameMode.speedChallenge)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.error.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '⏳ Thời gian: $_speedTimeLeft s',
                    style: const TextStyle(color: AppColors.error, fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                )
              else
                Text(
                  'Câu ${_currentIndex + 1}/${_questions.length}',
                  style: const TextStyle(color: AppColors.textSecondary, fontWeight: FontWeight.bold),
                ),
              if (_comboStreak > 1)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.tertiary.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    'Streak: $_comboStreak 🔥',
                    style: const TextStyle(color: AppColors.tertiary, fontWeight: FontWeight.bold, fontSize: 11),
                  ),
                ),
              Text(
                '+$_xpEarned XP',
                style: const TextStyle(color: AppColors.success, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Progress bar
          if (_selectedMode != GameMode.speedChallenge)
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: progress,
                backgroundColor: AppColors.surface,
                valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
                minHeight: 6,
              ),
            ),
          const SizedBox(height: 20),
          
          // Switch to custom game builders
          Expanded(
            child: _buildGameContent(),
          ),
        ],
      ),
    );
  }

  Widget _buildGameContent() {
    switch (_selectedMode!) {
      case GameMode.multipleChoice:
        return _buildMultipleChoiceView();
      case GameMode.matchPair:
      case GameMode.speedChallenge:
        return _buildMatchPairView();
      case GameMode.audioVocab:
        return _buildAudioVocabView();
      case GameMode.imageVocab:
        return _buildImageVocabView();
      case GameMode.sentenceMatching:
        return _buildSentenceMatchingView();
      case GameMode.memoryFlip:
        return _buildMemoryFlipView();
    }
  }

  // 1. Multiple Choice View
  Widget _buildMultipleChoiceView() {
    final q = _questions[_currentIndex];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(q.word, style: const TextStyle(color: Colors.white, fontSize: 36, fontWeight: FontWeight.w900), textAlign: TextAlign.center),
              const SizedBox(height: 8),
              Text(q.ipa, style: const TextStyle(color: AppColors.textSecondary, fontSize: 15, fontStyle: FontStyle.italic)),
              IconButton(
                icon: const Icon(Icons.volume_up_rounded, color: AppColors.primary, size: 28),
                onPressed: () => _playTts(q.word),
              ),
            ],
          ),
        ),
        _hasAnswered ? _buildFeedbackSection(q) : _buildOptionsSection(q),
      ],
    );
  }

  // 2 & 3. Match Pairs View
  Widget _buildMatchPairView() {
    return Column(
      children: [
        const Text(
          'Ghép từ bên trái với nghĩa đúng bên phải',
          textAlign: TextAlign.center,
          style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
        ),
        const SizedBox(height: 20),
        Expanded(
          child: Row(
            children: [
              // Cột English
              Expanded(
                child: ListView.builder(
                  itemCount: _leftCards.length,
                  itemBuilder: (context, index) {
                    final card = _leftCards[index];
                    return _buildPairPlayCard(card, _selectedLeft == card);
                  },
                ),
              ),
              const SizedBox(width: 16),
              // Cột Vietnamese
              Expanded(
                child: ListView.builder(
                  itemCount: _rightCards.length,
                  itemBuilder: (context, index) {
                    final card = _rightCards[index];
                    return _buildPairPlayCard(card, _selectedRight == card);
                  },
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPairPlayCard(GameCard card, bool isSelected) {
    Color cardColor = AppColors.surface;
    Color borderColors = Colors.white.withOpacity(0.05);
    Color textColor = AppColors.textPrimary;
    
    if (card.isMatched) {
      return AnimatedOpacity(
        opacity: 0.15,
        duration: const Duration(milliseconds: 300),
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.green.withOpacity(0.3)),
          ),
          child: Center(
            child: Text(
              card.text,
              style: const TextStyle(color: Colors.green, decoration: TextDecoration.lineThrough, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    if (isSelected) {
      cardColor = AppColors.primary.withOpacity(0.15);
      borderColors = AppColors.primary;
    } else if (card.status == CardStatus.correct) {
      cardColor = AppColors.success.withOpacity(0.2);
      borderColors = AppColors.success;
      textColor = AppColors.success;
    } else if (card.status == CardStatus.incorrect) {
      cardColor = AppColors.error.withOpacity(0.2);
      borderColors = AppColors.error;
      textColor = AppColors.error;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: cardColor,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          onTap: () => _handleMatchPairTap(card),
          borderRadius: BorderRadius.circular(14),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: borderColors, width: 1.5),
            ),
            child: Center(
              child: Text(
                card.text,
                style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 13),
                textAlign: TextAlign.center,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ),
        ),
      ),
    );
  }

  // 4. Audio Vocab View
  Widget _buildAudioVocabView() {
    final q = _questions[_currentIndex];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(color: AppColors.primary.withOpacity(0.1), shape: BoxShape.circle),
                child: IconButton(
                  icon: const Icon(Icons.volume_up_rounded, color: AppColors.primary, size: 50),
                  onPressed: () => _playTts(q.word),
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Lắng nghe và chọn nghĩa đúng',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 14),
              ),
            ],
          ),
        ),
        _hasAnswered ? _buildFeedbackSection(q) : _buildOptionsSection(q),
      ],
    );
  }

  // 5. Image Vocab View
  String _getImageSearchKeyword(String word) {
    final clean = word.trim().toLowerCase();
    
    // Bản đồ ánh xạ từ vựng sang các keyword cực kỳ cụ thể, trực quan và dễ tìm ảnh chất lượng cao
    const Map<String, String> keywordMap = {
      // A1
      "beginner": "student,classroom", "practice": "write,exercise", "vocabulary": "dictionary,book",
      "improve": "climbing,success", "welcome": "handshake,welcome", "language": "speak,alphabet",
      "simple": "minimalist", "friend": "friends,hug", "happy": "smile,happy",
      "learn": "classroom,books", "family": "family,children", "morning": "sunrise,morning",
      "school": "school,classroom", "summer": "beach,sun", "active": "running,workout",
      // A2
      "journey": "highway,road", "confident": "fist,winner", "habit": "calendar,clock",
      "encourage": "clapping,applause", "positive": "sunshine,smile", "healthy": "salad,fitness",
      "creative": "painting,artist", "success": "trophy,medal", "goal": "target,arrow",
      "experience": "camping,climbing", "patient": "hourglass,wait", "support": "help,teamwork",
      "believe": "praying,hope", "method": "blueprint,plan", "imagine": "dreaming,cloud",
      // B1
      "persistent": "marathon,runner", "collaborate": "meeting,teamwork", "effective": "checkmark,done",
      "challenge": "mountain,climbing", "achieve": "podium,medal", "determine": "compass,map",
      "essential": "water,drop", "progress": "stairs,chart", "valuable": "diamond,gem",
      "optimize": "gears,settings", "dynamic": "lightning,energy", "strategy": "chess,board",
      "productive": "office,workspace", "opportunity": "door,open", "flexibly": "yoga,stretching",
      // B2
      "substantial": "skyscraper,building", "fluency": "microphone,speaker", "analyze": "chart,dashboard",
      "evaluate": "checklist,exam", "alternative": "crossroads,arrows", "consequence": "domino,fall",
      "significant": "landmark,statue", "distinguish": "magnifying,lens", "innovative": "lightbulb,idea",
      "perspective": "telescope,stars", "professional": "suit,businessman", "sustainable": "recycle,green",
      "coherent": "puzzle,fit", "efficient": "stopwatch,clock", "implement": "construction,wrench",
      // C1
      "pragmatic": "toolbox,tools", "eloquent": "podium,speech", "cognitive": "brain,head",
      "sophisticated": "elegant,luxury", "ambiguous": "fog,mist", "comprehensive": "library,bookshelf",
      "ephemeral": "butterfly,dew", "inevitable": "sunset,dusk", "paradigm": "architecture,greek",
      "resilient": "oak,tree", "ubiquitous": "smartphone,app", "volatile": "volcano,eruption",
      "aesthetic": "art,gallery", "paradox": "mirror,reflection", "synthesis": "laboratory,chemical",
      // Travel & Topics
      "ticket": "ticket,flight", "hotel": "hotel,room", "bus": "bus,road",
      "map": "map,compass", "passport": "passport,travel", "fly": "airplane,sky",
      "beach": "beach,ocean", "bag": "suitcase,backpack", "airport": "airport,airplane",
      "luggage": "luggage,suitcase", "tourist": "tourist,camera", "flight": "airplane,flying",
      "station": "train,station", "guide": "guide,tour", "souvenir": "souvenir,gift",
      "destination": "island,resort", "itinerary": "calendar,map", "accommodation": "hotel,house",
      "explore": "hiking,backpack", "reservation": "reception,bell", "adventure": "rafting,kayak",
      "excursion": "bus,tour", "passenger": "passenger,airplane", "expedition": "tents,arctic",
      "picturesque": "scenery,village", "breathtaking": "mountains,canyon", "hospitable": "welcome,drinks",
      "spectacular": "fireworks,show", "wilderness": "forest,mountains", "sightseeing": "bus,sightseeing",
      "transcontinental": "globe,airplane", "sojourn": "cottage,stay", "uncharted": "island,sea",
      "peregrination": "traveler,backpack", "globetrotter": "world,traveler", "bespoke": "tailor,suit",
      "wanderlust": "traveler,map", "unspoiled": "beach,island", "vagabond": "traveler,road",
      // AI
      "robot": "robot,android", "smart": "smartphone,watch", "data": "servers,network",
      "code": "programming,code", "app": "smartphone,screen", "user": "user,avatar",
      "web": "internet,globe", "fast": "sports-car,speed", "computer": "computer,desk",
      "system": "gears,network", "network": "network,connected", "program": "code,screen",
      "digital": "digital,binary", "device": "tablet,phone", "storage": "hard-drive,cloud",
      "process": "cpu,chip", "automation": "robotic-arm,factory", "database": "database,server",
      "software": "software,cd", "interface": "ui,screen", "assistant": "smart-speaker,voice",
      "prediction": "crystal-ball,chart", "algorithm": "flowchart,math", "neural network": "brain,network",
      "machine learning": "robot,brain", "dataset": "spreadsheet,data", "optimization": "graph,arrow",
      "classification": "sorting,folders", "framework": "blueprint,wireframe", "generative": "ai,drawing",
      "autonomous": "self-driving-car", "cognitive computing": "brain,circuit", "deep learning": "neural-network,brain",
      "reinforcement": "reward,trophy", "transformers": "robot,sci-fi", "supervised": "labeled,tags",
      "natural language": "nlp,chat", "hyperparameters": "sliders,dials", "backpropagation": "gradient,graph"
    };

    return keywordMap[clean] ?? clean;
  }

  String _getEmojiForWord(String word) {
    final clean = word.trim().toLowerCase();
    const Map<String, String> emojiMap = {
      // A1
      "beginner": "🎓", "practice": "📝", "vocabulary": "📖",
      "improve": "📈", "welcome": "👋", "language": "🗣️",
      "simple": "✨", "friend": "🤝", "happy": "😊",
      "learn": "📚", "family": "👨‍👩‍👧‍👦", "morning": "🌅",
      "school": "🏫", "summer": "☀️", "active": "🏃",
      // A2
      "journey": "🛤️", "confident": "💪", "habit": "🔄",
      "encourage": "📣", "positive": "🌟", "healthy": "🥗",
      "creative": "🎨", "success": "🏆", "goal": "🎯",
      "experience": "🧗", "patient": "⏳", "support": "🤲",
      "believe": "🙏", "method": "🧩", "imagine": "💭",
      // B1
      "persistent": "🏋️", "collaborate": "👥", "effective": "✅",
      "challenge": "⛰️", "achieve": "🥇", "determine": "🧭",
      "essential": "💧", "progress": "🪜", "valuable": "💎",
      "optimize": "⚙️", "dynamic": "⚡", "strategy": "♟️",
      "productive": "💼", "opportunity": "🚪", "flexibly": "🧘",
      // B2
      "substantial": "🏗️", "fluency": "🎤", "analyze": "📊",
      "evaluate": "📋", "alternative": "🔀", "consequence": "🎲",
      "significant": "🗽", "distinguish": "🔍", "innovative": "💡",
      "perspective": "🔭", "professional": "👔", "sustainable": "♻️",
      "coherent": "🧩", "efficient": "⏱️", "implement": "🔧",
      // C1
      "pragmatic": "🛠️", "eloquent": "🎙️", "cognitive": "🧠",
      "sophisticated": "🎩", "ambiguous": "🌫️", "comprehensive": "🌐",
      "ephemeral": "🦋", "inevitable": "🌇", "paradigm": "🏛️",
      "resilient": "🌳", "ubiquitous": "📱", "volatile": "🌋",
      "aesthetic": "🖼️", "paradox": "🪞", "synthesis": "🧪",
      // Travel & Topics
      "ticket": "🎫", "hotel": "🏨", "bus": "🚌", "map": "🗺️", "passport": "🛂", "fly": "✈️", "beach": "🏖️", "bag": "🎒",
      "airport": "🛃", "luggage": "🧳", "tourist": "📸", "flight": "🛩️", "station": "🚉", "guide": "🎴", "souvenir": "🎁",
      "destination": "🏝️", "itinerary": "📅", "accommodation": "🏠", "explore": "🥾", "reservation": "🔔", "adventure": "🚣",
      "excursion": "🚐", "passenger": "🧑‍🚀", "expedition": "⛺", "picturesque": "🏞️", "breathtaking": "🧗", "hospitable": "🍵",
      "spectacular": "🎆", "wilderness": "🌲", "sightseeing": "📸", "transcontinental": "🌐", "sojourn": "🏡", "uncharted": "⛵",
      "peregrination": "🎒", "globetrotter": "🌍", "bespoke": "🪡", "wanderlust": "🗺️", "unspoiled": "🏖️", "vagabond": "🚶",
      // AI
      "robot": "🤖", "smart": "⌚", "data": "🖥️", "code": "💻", "app": "📱", "user": "👤", "web": "🕸️", "fast": "🏎️",
      "computer": "🖥️", "system": "⚙️", "network": "🕸️", "program": "💾", "digital": "🔢", "device": "🔌", "storage": "💾",
      "process": "🎛️", "automation": "🦾", "database": "🗄️", "software": "📀", "interface": "🖥️", "assistant": "🎙️",
      "prediction": "🔮", "algorithm": "🧮", "neural network": "🧠", "machine learning": "🤖", "dataset": "📊", "optimization": "📈",
      "classification": "🗂️", "framework": "🧱", "generative": "🎨", "autonomous": "🚗", "cognitive computing": "🧠", "deep learning": "🧠",
      "reinforcement": "🏆", "transformers": "🤖", "supervised": "🏷️", "natural language": "💬", "hyperparameters": "🎛️", "backpropagation": "📉"
    };
    return emojiMap[clean] ?? "📷";
  }

  // Khai báo state phụ để lưu trữ xem người dùng có yêu cầu xem Gợi ý hay không
  bool _showHint = false;

  Widget _buildImageVocabView() {
    final q = _questions[_currentIndex];
    
    final keyword = _getImageSearchKeyword(q.word);
    final imageUrl = 'https://loremflickr.com/320/240/$keyword';
    final emoji = _getEmojiForWord(q.word);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          child: SingleChildScrollView(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(height: 10),
                ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: _SafeNetworkImage(
                    primaryUrl: imageUrl,
                    emoji: emoji,
                    height: 180,
                    width: 240,
                    fit: BoxFit.cover,
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  'Chọn từ tiếng Anh phù hợp với hình ảnh',
                  style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                ),
                const SizedBox(height: 10),
                
                // NÚT BẤM GỢI Ý THÔNG MINH khi ảnh ngẫu nhiên hoặc trừu tượng
                if (!_hasAnswered)
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 300),
                    child: _showHint
                        ? Container(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                            decoration: BoxDecoration(
                              color: AppColors.primary.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: AppColors.primary.withOpacity(0.3)),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  'Gợi ý: $emoji  "${q.correctAnswer}"',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 14,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                InkWell(
                                  onTap: () {
                                    setState(() {
                                      _showHint = false;
                                    });
                                  },
                                  child: const Icon(Icons.close_rounded, size: 16, color: Colors.white70),
                                )
                              ],
                            ),
                          )
                        : TextButton.icon(
                            onPressed: () {
                              setState(() {
                                _showHint = true;
                              });
                            },
                            icon: const Icon(Icons.lightbulb_outline_rounded, color: AppColors.primary, size: 18),
                            label: const Text(
                              'Hình ảnh chưa rõ ràng? Xem gợi ý',
                              style: TextStyle(color: AppColors.primary, fontSize: 12, fontWeight: FontWeight.bold),
                            ),
                          ),
                  ),
                const SizedBox(height: 10),
              ],
            ),
          ),
        ),
        _hasAnswered
            ? _buildFeedbackSection(q)
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: (q.englishOptions ?? [q.word]).map((opt) {
                  return Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    child: ElevatedButton(
                      onPressed: () {
                        // Reset hint khi bấm trả lời
                        setState(() {
                          _showHint = false;
                        });
                        _submitSelection(opt);
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.surface,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 18),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                          side: BorderSide(color: Colors.white.withOpacity(0.05)),
                        ),
                      ),
                      child: Text(
                        opt,
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                      ),
                    ),
                  );
                }).toList(),
              ),
      ],
    );
  }



  // 6. Sentence Matching View
  Widget _buildSentenceMatchingView() {
    final q = _questions[_currentIndex];
    // Ẩn từ khóa chính trong câu ví dụ để tăng độ khó
    final maskedSentence = q.example.replaceAll(
      RegExp(q.word, caseSensitive: false),
      '_______',
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.white.withOpacity(0.05)),
                ),
                child: Text(
                  maskedSentence,
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontStyle: FontStyle.italic, height: 1.5),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Điền từ tiếng Anh còn thiếu vào câu',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
            ],
          ),
        ),
        _hasAnswered ? _buildFeedbackSection(q) : _buildEnglishOptionsSection(q),
      ],
    );
  }

  Widget _buildEnglishOptionsSection(Question question) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: (question.englishOptions ?? [question.word]).map((opt) {
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          child: ElevatedButton(
            onPressed: () => _submitSelection(opt),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.surface,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
                side: BorderSide(color: Colors.white.withOpacity(0.05)),
              ),
              elevation: 0,
            ),
            child: Text(
              opt,
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
              textAlign: TextAlign.center,
            ),
          ),
        );
      }).toList(),
    );
  }

  // 7. Memory Flip Cards View
  Widget _buildMemoryFlipView() {
    return Column(
      children: [
        const Text(
          'Lật cặp thẻ tiếng Anh và nghĩa tiếng Việt tương ứng',
          textAlign: TextAlign.center,
          style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
        ),
        const SizedBox(height: 20),
        Expanded(
          child: GridView.builder(
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 0.85,
            ),
            itemCount: _memoryCards.length,
            itemBuilder: (context, index) {
              final card = _memoryCards[index];
              return _buildMemoryCardWidget(card, index);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildMemoryCardWidget(MemoryCard card, int index) {
    if (card.isMatched) {
      return Container(
        decoration: BoxDecoration(
          color: AppColors.success.withOpacity(0.1),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.success.withOpacity(0.3)),
        ),
        child: const Center(
          child: Icon(Icons.check_rounded, color: AppColors.success, size: 30),
        ),
      );
    }

    return GestureDetector(
      onTap: () => _handleMemoryFlipTap(index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        decoration: BoxDecoration(
          color: card.isFlipped ? AppColors.surface : AppColors.primary.withOpacity(0.2),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: card.isFlipped ? AppColors.primary : AppColors.primary.withOpacity(0.4),
            width: 1.5,
          ),
        ),
        child: Center(
          child: card.isFlipped
              ? Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: Text(
                    card.text,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                    textAlign: TextAlign.center,
                  ),
                )
              : const Icon(Icons.help_outline_rounded, color: Colors.white54, size: 28),
        ),
      ),
    );
  }

  Widget _buildOptionsSection(Question question) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: question.options.map((opt) {
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          child: ElevatedButton(
            onPressed: () => _submitSelection(opt),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.surface,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
                side: BorderSide(color: Colors.white.withOpacity(0.05)),
              ),
              elevation: 0,
            ),
            child: Text(
              opt,
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
              textAlign: TextAlign.center,
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildFeedbackSection(Question question) {
    final statusColor = _isAnswerCorrect ? AppColors.success : AppColors.error;
    final message = _isAnswerCorrect ? '✓ Chính xác!' : 'Bạn gần đúng rồi 😊';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        FadeInUp(
          duration: const Duration(milliseconds: 300),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: statusColor.withOpacity(0.12),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: statusColor.withOpacity(0.3), width: 1.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      _isAnswerCorrect ? Icons.check_circle_rounded : Icons.info_outline_rounded,
                      color: statusColor,
                      size: 22,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      message,
                      style: TextStyle(color: statusColor, fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  '${question.word} = ${question.correctAnswer}',
                  style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 6),
                Text(
                  'Ví dụ:\n"${question.example}"',
                  style: const TextStyle(color: AppColors.textPrimary, fontSize: 13, fontStyle: FontStyle.italic),
                ),
                if (!_isAnswerCorrect) ...[
                  const SizedBox(height: 8),
                  Text(
                    question.explanation,
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        ElevatedButton(
          onPressed: _nextQuestion,
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 18),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                _currentIndex < _questions.length - 1 ? 'Tiếp tục' : 'Hoàn thành kết quả',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.arrow_forward_rounded, size: 20),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildGameOverState() {
    final totalQuestions = _attempts.length;
    final correctCount = _attempts.where((a) => a.isCorrect).length;
    final accuracyRate = totalQuestions > 0 ? (correctCount / totalQuestions * 100.0) : 100.0;
    
    final wrongList = _attempts.where((a) => !a.isCorrect).toList();
    final correctList = _attempts.where((a) => a.isCorrect).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header Congratulation
          ZoomIn(
            child: Center(
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.success.withOpacity(0.12),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.emoji_events_rounded, size: 64, color: AppColors.tertiary),
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'BÁO CÁO HỌC TẬP AI 📊',
            style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 4),
          Text(
            'Buổi học trình độ ${widget.level} đã hoàn thành',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),

          // Accuracy Circle Chart & XP + Combo
          Row(
            children: [
              // Chart
              Container(
                width: 100,
                height: 100,
                child: CustomPaint(
                  painter: AccuracyRingPainter(
                    accuracy: accuracyRate,
                    color: accuracyRate >= 80 ? AppColors.success : AppColors.primary,
                  ),
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          '${accuracyRate.toStringAsFixed(0)}%',
                          style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900),
                        ),
                        const Text(
                          'Độ chính xác',
                          style: TextStyle(color: AppColors.textSecondary, fontSize: 9),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 20),
              // Stats
              Expanded(
                child: Column(
                  children: [
                    _buildReportStatRow('Từ đã học', '$totalQuestions từ', Icons.menu_book_rounded, AppColors.primary),
                    const SizedBox(height: 8),
                    _buildReportStatRow('Câu đúng', '$correctCount/$totalQuestions', Icons.check_circle_rounded, AppColors.success),
                    const SizedBox(height: 8),
                    _buildReportStatRow('Kinh nghiệm', '+$_xpEarned XP', Icons.offline_bolt_rounded, AppColors.tertiary),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // AI Insights
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.white.withOpacity(0.05)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.psychology_rounded, color: AppColors.primary, size: 22),
                    SizedBox(width: 8),
                    Text(
                      'AI Insights & Đề xuất 🧠',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                // Điểm yếu
                Text(
                  wrongList.isNotEmpty 
                      ? '⚠️ Phát hiện điểm yếu:\nBạn đang gặp chút khó khăn ở một số từ vựng. Cần tăng độ phản xạ nhạy bén hơn.'
                      : '✅ Điểm yếu: Không có! Trí nhớ phản xạ của bạn cực kỳ xuất sắc.',
                  style: const TextStyle(color: AppColors.textPrimary, fontSize: 13, height: 1.4),
                ),
                const SizedBox(height: 10),
                // Gợi ý ôn tập
                if (wrongList.isNotEmpty) ...[
                  Text(
                    '🔄 Từ cần ôn lại: ${wrongList.map((a) => a.word).take(3).join(', ')}.',
                    style: const TextStyle(color: AppColors.tertiary, fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 10),
                ],
                // Đề xuất chủ đề tiếp theo
                const Text(
                  '🚀 Đề xuất chủ đề tiếp theo:\nHãy thử sức với chủ đề "Công nghệ", "AI" hoặc "Kinh doanh" để mở rộng vốn từ.',
                  style: TextStyle(color: AppColors.textSecondary, fontSize: 12, height: 1.4),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Học viên đã làm chủ tốt (Mastered)
          if (correctList.isNotEmpty) ...[
            const Text('Từ đã thuộc trong buổi học ✅', style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: correctList.map((item) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.success.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    item.word,
                    style: const TextStyle(color: AppColors.success, fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),
          ],

          // Từ cần ôn lại
          if (wrongList.isNotEmpty) ...[
            const Text('Từ cần ôn lại sớm 🔄', style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: wrongList.map((item) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.error.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    item.word,
                    style: const TextStyle(color: AppColors.error, fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),
          ],

          // Buttons
          ElevatedButton(
            onPressed: () => _initGame(_selectedMode!),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            child: const Text('Chơi lại', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
          ),
          const SizedBox(height: 12),
          TextButton(
            onPressed: () {
              setState(() {
                _selectedMode = null;
              });
            },
            child: const Text('Đổi chế độ chơi', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold)),
          ),
          TextButton(
            onPressed: () => context.pop(),
            child: const Text('Quay lại kho từ vựng', style: TextStyle(color: AppColors.textSecondary)),
          ),
        ],
      ),
    );
  }

  Widget _buildReportStatRow(String label, String value, IconData icon, Color color) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: color.withOpacity(0.15), shape: BoxShape.circle),
          child: Icon(icon, color: color, size: 16),
        ),
        const SizedBox(width: 10),
        Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
        const Spacer(),
        Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
      ],
    );
  }
}

class AccuracyRingPainter extends CustomPainter {
  final double accuracy;
  final Color color;

  AccuracyRingPainter({required this.accuracy, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    
    final bgPaint = Paint()
      ..color = Colors.white.withOpacity(0.05)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8;
    canvas.drawCircle(center, radius - 4, bgPaint);

    final arcPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 8;
      
    final sweepAngle = (accuracy / 100.0) * 2 * 3.1415926535;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius - 4),
      -3.1415926535 / 2,
      sweepAngle,
      false,
      arcPaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

// Memory flip card model
class MemoryCard {
  final int id;
  final String text;
  final bool isEnglish;
  bool isFlipped;
  bool isMatched;

  MemoryCard({
    required this.id,
    required this.text,
    required this.isEnglish,
    this.isFlipped = false,
    this.isMatched = false,
  });
}

class Question {
  final String word;
  final String ipa;
  final String correctAnswer;
  final List<String> options;
  final String example;
  final String explanation;
  List<String>? englishOptions;

  Question({
    required this.word,
    required this.ipa,
    required this.correctAnswer,
    required this.options,
    required this.example,
    required this.explanation,
    this.englishOptions,
  });

  factory Question.fromJson(Map<String, dynamic> json) {
    return Question(
      word: json['word'] ?? '',
      ipa: json['ipa'] ?? '',
      correctAnswer: json['correct_answer'] ?? '',
      options: List<String>.from(json['options'] ?? []),
      example: json['example'] ?? '',
      explanation: json['explanation'] ?? '',
    );
  }
}

enum CardStatus { normal, selected, correct, incorrect }

class GameCard {
  final int id;
  final String text;
  final bool isEnglish;
  bool isMatched;
  CardStatus status;

  GameCard({
    required this.id,
    required this.text,
    required this.isEnglish,
    this.isMatched = false,
    this.status = CardStatus.normal,
  });
}

class Attempt {
  final String word;
  final String userAnswer;
  final bool isCorrect;

  Attempt({
    required this.word,
    required this.userAnswer,
    required this.isCorrect,
  });

  Map<String, dynamic> toJson() {
    return {
      'word': word,
      'user_answer': userAnswer,
      'is_correct': isCorrect,
    };
  }
}

class _SafeNetworkImage extends StatefulWidget {
  final String primaryUrl;
  final String emoji;
  final double height;
  final double width;
  final BoxFit fit;

  const _SafeNetworkImage({
    Key? key,
    required this.primaryUrl,
    required this.emoji,
    required this.height,
    required this.width,
    required this.fit,
  }) : super(key: key);

  @override
  _SafeNetworkImageState createState() => _SafeNetworkImageState();
}

class _SafeNetworkImageState extends State<_SafeNetworkImage> {
  bool _useFallback = false;

  @override
  void didUpdateWidget(_SafeNetworkImage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.primaryUrl != oldWidget.primaryUrl) {
      setState(() {
        _useFallback = false;
      });
    }
  }

  Widget _buildEmojiCard() {
    return Container(
      height: widget.height,
      width: widget.width,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppColors.primary.withOpacity(0.3),
            AppColors.surface,
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.primary.withOpacity(0.2)),
      ),
      child: Center(
        child: Text(
          widget.emoji,
          style: const TextStyle(fontSize: 64),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_useFallback) {
      return _buildEmojiCard();
    }

    return Image.network(
      widget.primaryUrl,
      height: widget.height,
      width: widget.width,
      fit: widget.fit,
      loadingBuilder: (context, child, loadingProgress) {
        if (loadingProgress == null) return child;
        return Container(
          height: widget.height,
          width: widget.width,
          color: AppColors.surface,
          child: const Center(
            child: SizedBox(
              height: 20,
              width: 20,
              child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
            ),
          ),
        );
      },
      errorBuilder: (context, error, stackTrace) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted && !_useFallback) {
            setState(() {
              _useFallback = true;
            });
          }
        });
        return _buildEmojiCard();
      },
    );
  }
}

