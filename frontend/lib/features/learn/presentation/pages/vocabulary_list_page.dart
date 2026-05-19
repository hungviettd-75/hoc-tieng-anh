import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:ai_english_coach/core/api_config.dart';
import 'package:ai_english_coach/features/auth/services/auth_service.dart';
import 'package:animate_do/animate_do.dart';
import 'package:audioplayers/audioplayers.dart';

class VocabularyListPage extends StatefulWidget {
  final String title;
  
  const VocabularyListPage({
    super.key, 
    this.title = 'Kho từ vựng thông minh',
  });

  @override
  State<VocabularyListPage> createState() => _VocabularyListPageState();
}

class _VocabularyListPageState extends State<VocabularyListPage> {
  String _selectedLevel = 'B1';
  bool _isLoading = false;
  String _errorMessage = '';
  List<Map<String, dynamic>> _vocabList = [];
  final AudioPlayer _audioPlayer = AudioPlayer();
  String? _currentlyPlayingWord;

  @override
  void initState() {
    super.initState();
    _fetchVocabulary();
  }

  @override
  void dispose() {
    _audioPlayer.stop();
    _audioPlayer.dispose();
    super.dispose();
  }

  Future<void> _fetchVocabulary() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
      _vocabList = []; // Xóa danh sách cũ để tránh dùng sai dữ liệu khi bấm nhanh
    });
    try {
      final token = await AuthService().getAccessToken();
      final headers = {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

      final response = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/learn/vocabulary?level=$_selectedLevel'),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        setState(() {
          _vocabList = data.map((item) => Map<String, dynamic>.from(item)).toList();
          _isLoading = false;
        });
      } else {
        setState(() {
          _errorMessage = 'Không thể tải dữ liệu từ server';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Lỗi kết nối. Vui lòng kiểm tra lại mạng';
        _isLoading = false;
      });
    }
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
          onPressed: () => context.pop(),
        ),
        title: Text(widget.title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
      body: Column(
        children: [
          _buildLevelSelector(),
          Expanded(
            child: Stack(
              children: [
                _isLoading
                  ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
                  : _errorMessage.isNotEmpty
                    ? _buildErrorState()
                    : _vocabList.isEmpty 
                      ? _buildEmptyState()
                      : ListView.builder(
                          padding: const EdgeInsets.fromLTRB(20, 10, 20, 100),
                          itemCount: _vocabList.length,
                          itemBuilder: (context, index) {
                            final item = _vocabList[index];
                            return FadeInUp(
                              delay: Duration(milliseconds: 100 * index),
                              child: _buildVocabCard(item),
                            );
                          },
                        ),
                _buildAICoachButton(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLevelSelector() {
    final levels = ['A1', 'A2', 'B1', 'B2', 'C1'];
    return Container(
      height: 50,
      margin: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          Expanded(
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: levels.length,
              itemBuilder: (context, index) {
                final level = levels[index];
                final isSelected = _selectedLevel == level;
                return Padding(
                  padding: const EdgeInsets.only(right: 10),
                  child: ChoiceChip(
                    label: Text(level),
                    selected: isSelected,
                    onSelected: (selected) {
                      if (selected) {
                        setState(() => _selectedLevel = level);
                        _fetchVocabulary();
                      }
                    },
                    selectedColor: AppColors.primary,
                    backgroundColor: AppColors.surface,
                    labelStyle: TextStyle(
                      color: isSelected ? Colors.white : Colors.white54,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                );
              },
            ),
          ),
          // Nút "Đổi từ vựng 🔄" cao cấp, ngẫu nhiên hóa từ vựng hiện tại
          Container(
            margin: const EdgeInsets.only(right: 16),
            child: IconButton(
              icon: const Icon(Icons.cached_rounded, color: AppColors.primary, size: 24),
              tooltip: 'Đổi từ vựng ngẫu nhiên',
              style: IconButton.styleFrom(
                backgroundColor: AppColors.surface,
                padding: const EdgeInsets.all(12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                side: BorderSide(color: AppColors.primary.withOpacity(0.3)),
              ),
              onPressed: () {
                _fetchVocabulary();
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: const Text('🔄 Đã làm mới và xáo trộn từ vựng thông minh!'),
                    backgroundColor: AppColors.primary,
                    duration: const Duration(seconds: 1),
                    behavior: SnackBarBehavior.floating,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.lock_outline_rounded, size: 64, color: Colors.white10),
          const SizedBox(height: 16),
          Text(
            'Cấp độ $_selectedLevel chưa được mở khóa',
            style: TextStyle(color: Colors.white38, fontSize: 16),
          ),
          const SizedBox(height: 8),
          const Text(
            'Hãy tiếp tục học để bổ sung từ vựng mới!',
            style: TextStyle(color: Colors.white24, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.cloud_off_rounded, size: 64, color: Colors.white24),
          const SizedBox(height: 16),
          Text(
            _errorMessage,
            style: const TextStyle(color: Colors.white54, fontSize: 15),
          ),
          const SizedBox(height: 12),
          ElevatedButton.icon(
            onPressed: _fetchVocabulary,
            icon: const Icon(Icons.refresh),
            label: const Text('Thử lại'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
            ),
          )
        ],
      ),
    );
  }

  Widget _buildAICoachButton() {
    return Positioned(
      bottom: 20,
      left: 20,
      right: 20,
      child: FadeInUp(
        child: ElevatedButton(
          onPressed: _isLoading
              ? null
              : () {
                  if (_vocabList.isEmpty) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Vui lòng đợi danh sách từ vựng được tải xong!')),
                    );
                    return;
                  }

                  // Lọc và chỉ lấy tối đa 5 từ cần luyện tập nhất (ưu tiên 'Learning' -> 'New' -> 'Mastered')
                  final List<Map<String, dynamic>> sortedVocabs = List.from(_vocabList);
                  sortedVocabs.sort((a, b) {
                    final statusA = a['status'] ?? 'New';
                    final statusB = b['status'] ?? 'New';
                    
                    int priority(String status) {
                      if (status == 'Learning') return 1;
                      if (status == 'New') return 2;
                      return 3;
                    }
                    
                    return priority(statusA).compareTo(priority(statusB));
                  });

                  final List<String> targetWords = sortedVocabs
                      .take(5)
                      .map((item) => item['word'] as String)
                      .toList();
                      
                  final String wordsParam = targetWords.join(',');
                  
                  // Context-aware deep linking to vocabulary practice chat session with current dynamic words
                  context.push('/chat?mode=vocabulary_practice&level=$_selectedLevel&words=${Uri.encodeComponent(wordsParam)}');
                },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 18),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            elevation: 8,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.psychology_rounded),
              const SizedBox(width: 12),
              Text('Luyện tập từ vựng trình độ $_selectedLevel cùng AI', style: const TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildVocabCard(Map<String, dynamic> item) {
    Color statusColor;
    String statusText;
    switch (item['status']) {
      case 'Mastered':
        statusColor = Colors.green;
        statusText = 'Đã thuộc';
        break;
      case 'Learning':
        statusColor = Colors.orange;
        statusText = 'Đang học';
        break;
      default:
        statusColor = AppColors.primary;
        statusText = 'Từ mới';
    }

    final isPlaying = _currentlyPlayingWord == item['word'];

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Row(
                  children: [
                    Flexible(
                      child: Text(
                        item['word']!,
                        style: const TextStyle(color: AppColors.primary, fontSize: 22, fontWeight: FontWeight.bold),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      icon: Icon(
                        isPlaying ? Icons.volume_up_rounded : Icons.volume_up_outlined,
                        color: isPlaying ? AppColors.primary : Colors.white54,
                        size: 20,
                      ),
                      onPressed: () async {
                        if (isPlaying) {
                          await _audioPlayer.stop();
                          setState(() {
                            _currentlyPlayingWord = null;
                          });
                        } else {
                          try {
                            await _audioPlayer.stop();
                            setState(() {
                              _currentlyPlayingWord = item['word'];
                            });
                            final url = '${ApiConfig.speaking}/tts?text=${Uri.encodeComponent(item['word'])}';
                            await _audioPlayer.play(UrlSource(url)).catchError((e) {
                              if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('Không thể phát âm thanh: $e')),
                                );
                              }
                            });
                            _audioPlayer.onPlayerComplete.first.then((_) {
                              if (mounted && _currentlyPlayingWord == item['word']) {
                                setState(() {
                                  _currentlyPlayingWord = null;
                                });
                              }
                            });
                          } catch (e) {
                            print("ERROR playing vocab TTS: $e");
                            if (mounted) {
                              setState(() {
                                _currentlyPlayingWord = null;
                              });
                            }
                          }
                        }
                      },
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(color: statusColor.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
                child: Text(statusText, style: TextStyle(color: statusColor, fontSize: 10, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(item['ipa']!, style: const TextStyle(color: Colors.white54, fontSize: 14, fontStyle: FontStyle.italic)),
          const SizedBox(height: 12),
          Text(item['meaning']!, style: const TextStyle(color: AppColors.textPrimary, fontSize: 16, fontWeight: FontWeight.w500)),
          const SizedBox(height: 12),
          _buildExampleBox(item['example']!),
        ],
      ),
    );
  }

  Widget _buildExampleBox(String example) {
    return Container(
      padding: const EdgeInsets.all(12),
      width: double.infinity,
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.03), borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Ví dụ:', style: TextStyle(color: Colors.white38, fontSize: 12)),
          const SizedBox(height: 4),
          Text(example, style: const TextStyle(color: AppColors.textSecondary, fontSize: 14, height: 1.4)),
        ],
      ),
    );
  }
}
