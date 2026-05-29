import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:ai_english_coach/features/learn/presentation/providers/learn_provider.dart';
import 'package:animate_do/animate_do.dart';

class RoleplayTopic {
  final String id;
  final String title;
  final String englishTitle;
  final IconData icon;
  final Color color;

  const RoleplayTopic({
    required this.id,
    required this.title,
    required this.englishTitle,
    required this.icon,
    required this.color,
  });
}

class LevelOption {
  final String code;
  final String title;
  final String name;
  final String description;
  final IconData icon;
  final Color color;

  const LevelOption({
    required this.code,
    required this.title,
    required this.name,
    required this.description,
    required this.icon,
    required this.color,
  });
}

class DurationOption {
  final int minutes;
  final String title;
  final String label;
  final IconData icon;
  final Color color;

  const DurationOption({
    required this.minutes,
    required this.title,
    required this.label,
    required this.icon,
    required this.color,
  });
}

enum TopicFilter { all, favorites, recents }

class RoleplaySetupPage extends ConsumerStatefulWidget {
  const RoleplaySetupPage({super.key});

  @override
  ConsumerState<RoleplaySetupPage> createState() => _RoleplaySetupPageState();
}

class _RoleplaySetupPageState extends ConsumerState<RoleplaySetupPage> {
  // Wizard State
  int _currentStep = 0; // 0: Select Topic, 1: Select Level, 2: Select Duration, 3: Lesson Plan
  RoleplayTopic? _selectedTopic;
  String? _selectedLevel;
  int? _selectedDuration;

  // Step 1: Select Topic state
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  TopicFilter _selectedFilter = TopicFilter.all;
  List<String> _favoriteIds = [];
  List<String> _recentIds = [];
  bool _isLoading = true;
  bool _isSubmitting = false;

  static const List<RoleplayTopic> _allTopics = [
    RoleplayTopic(id: 'culture', title: 'Văn hóa', englishTitle: 'Culture', icon: Icons.temple_buddhist_rounded, color: Colors.orange),
    RoleplayTopic(id: 'cooking', title: 'Nấu ăn', englishTitle: 'Cooking', icon: Icons.restaurant_rounded, color: Colors.redAccent),
    RoleplayTopic(id: 'cuisine', title: 'Ẩm thực', englishTitle: 'Cuisine', icon: Icons.fastfood_rounded, color: Colors.amber),
    RoleplayTopic(id: 'travel', title: 'Du lịch', englishTitle: 'Travel', icon: Icons.flight_takeoff_rounded, color: Colors.blue),
    RoleplayTopic(id: 'shopping', title: 'Mua sắm', englishTitle: 'Shopping', icon: Icons.shopping_bag_rounded, color: Colors.pink),
    RoleplayTopic(id: 'movies', title: 'Phim ảnh', englishTitle: 'Movies & Cinema', icon: Icons.movie_rounded, color: Colors.deepPurple),
    RoleplayTopic(id: 'pets', title: 'Thú cưng', englishTitle: 'Pets', icon: Icons.pets_rounded, color: Colors.brown),
    RoleplayTopic(id: 'technology', title: 'Công nghệ', englishTitle: 'Technology', icon: Icons.computer_rounded, color: Colors.teal),
    RoleplayTopic(id: 'sports', title: 'Thể thao', englishTitle: 'Sports', icon: Icons.sports_soccer_rounded, color: Colors.green),
    RoleplayTopic(id: 'music', title: 'Âm nhạc', englishTitle: 'Music', icon: Icons.music_note_rounded, color: Colors.indigo),
    RoleplayTopic(id: 'fitness', title: 'Sức khỏe & thể chất', englishTitle: 'Health & Fitness', icon: Icons.fitness_center_rounded, color: Colors.lightBlue),
    RoleplayTopic(id: 'fashion', title: 'Thời trang', englishTitle: 'Fashion', icon: Icons.checkroom_rounded, color: Colors.purple),
    RoleplayTopic(id: 'career', title: 'Việc làm & nghề nghiệp', englishTitle: 'Jobs & Careers', icon: Icons.work_rounded, color: Colors.blueGrey),
    RoleplayTopic(id: 'environment', title: 'Môi trường', englishTitle: 'Environment', icon: Icons.eco_rounded, color: Colors.lightGreen),
    RoleplayTopic(id: 'history', title: 'Lịch sử', englishTitle: 'History', icon: Icons.history_edu_rounded, color: Colors.deepOrange),
    RoleplayTopic(id: 'social_media', title: 'Mạng xã hội', englishTitle: 'Social Media', icon: Icons.share_rounded, color: Colors.blueAccent),
    RoleplayTopic(id: 'art', title: 'Nghệ thuật & sáng tạo', englishTitle: 'Art & Creativity', icon: Icons.palette_rounded, color: Colors.pinkAccent),
    RoleplayTopic(id: 'science', title: 'Khoa học', englishTitle: 'Science', icon: Icons.science_rounded, color: Colors.cyan),
    RoleplayTopic(id: 'literature', title: 'Văn học', englishTitle: 'Literature', icon: Icons.menu_book_rounded, color: Colors.orangeAccent),
    RoleplayTopic(id: 'languages', title: 'Ngôn ngữ', englishTitle: 'Languages', icon: Icons.translate_rounded, color: Colors.lightBlueAccent),
    RoleplayTopic(id: 'politics', title: 'Chính trị', englishTitle: 'Politics', icon: Icons.gavel_rounded, color: Colors.grey),
    RoleplayTopic(id: 'psychology', title: 'Tâm lý học', englishTitle: 'Psychology', icon: Icons.psychology_rounded, color: Colors.indigoAccent),
    RoleplayTopic(id: 'philosophy', title: 'Triết học', englishTitle: 'Philosophy', icon: Icons.self_improvement_rounded, color: Colors.tealAccent),
    RoleplayTopic(id: 'sociology', title: 'Xã hội học', englishTitle: 'Sociology', icon: Icons.people_rounded, color: Colors.cyanAccent),
    RoleplayTopic(id: 'startup', title: 'Khởi nghiệp', englishTitle: 'Startups', icon: Icons.lightbulb_rounded, color: Colors.amberAccent),
    RoleplayTopic(id: 'news', title: 'Tin tức', englishTitle: 'News', icon: Icons.newspaper_rounded, color: Colors.red),
    RoleplayTopic(id: 'finance', title: 'Tài chính', englishTitle: 'Finance & Money', icon: Icons.monetization_on_rounded, color: Colors.greenAccent),
    RoleplayTopic(id: 'astronomy', title: 'Thiên văn học', englishTitle: 'Astronomy', icon: Icons.rocket_launch_rounded, color: Colors.deepPurpleAccent),
    RoleplayTopic(id: 'math', title: 'Toán học', englishTitle: 'Mathematics', icon: Icons.calculate_rounded, color: Colors.blue),
    RoleplayTopic(id: 'architecture', title: 'Kiến trúc', englishTitle: 'Architecture', icon: Icons.architecture_rounded, color: Colors.amber),
    RoleplayTopic(id: 'animation', title: 'Hoạt hình', englishTitle: 'Animation & Cartoons', icon: Icons.animation_rounded, color: Colors.pink),
    RoleplayTopic(id: 'marketing', title: 'Marketing', englishTitle: 'Marketing', icon: Icons.campaign_rounded, color: Colors.purpleAccent),
    RoleplayTopic(id: 'journalism', title: 'Báo chí', englishTitle: 'Journalism', icon: Icons.article_rounded, color: Colors.blueGrey),
    RoleplayTopic(id: 'software', title: 'Phần mềm', englishTitle: 'Software Development', icon: Icons.code_rounded, color: Colors.green),
  ];

  static const List<LevelOption> _levels = [
    LevelOption(code: 'A1', title: 'Mới bắt đầu (A1)', name: 'Mới bắt đầu', description: 'AI nói cực kỳ chậm, câu ngắn đơn giản và có dịch Tiếng Việt hỗ trợ.', icon: Icons.sentiment_satisfied_alt_rounded, color: Colors.green),
    LevelOption(code: 'A2', title: 'Sơ trung cấp (A2)', name: 'Sơ trung cấp', description: 'AI nói chậm, câu ngắn rõ ràng để luyện phản xạ nghe hiểu căn bản.', icon: Icons.sentiment_satisfied_rounded, color: Colors.teal),
    LevelOption(code: 'B1', title: 'Trung cấp (B1)', name: 'Trung cấp', description: 'AI nói tốc độ vừa phải, dùng từ giao tiếp đời sống thông dụng.', icon: Icons.sentiment_neutral_rounded, color: Colors.orange),
    LevelOption(code: 'B2', title: 'Trung cao cấp (B2)', name: 'Trung cao cấp', description: 'AI nói tốc độ tự nhiên, từ vựng phong phú để thảo luận sâu.', icon: Icons.sentiment_neutral_rounded, color: Colors.deepOrange),
    LevelOption(code: 'C1', title: 'Nâng cao (C1)', name: 'Nâng cao', description: 'AI nói tốc độ tự nhiên bản xứ, từ vựng học thuật & thành ngữ.', icon: Icons.sentiment_very_satisfied_rounded, color: Colors.purple),
    LevelOption(code: 'C2', title: 'Thông thạo (C2)', name: 'Thông thạo', description: 'Thử thách đỉnh cao với tốc độ nhanh, thành ngữ phức tạp & tiếng lóng.', icon: Icons.star_rounded, color: Colors.pink),
  ];

  static const List<DurationOption> _durations = [
    DurationOption(minutes: 5, title: '5 phút', label: 'Khởi động nhanh', icon: Icons.timer_outlined, color: Colors.blue),
    DurationOption(minutes: 10, title: '10 phút', label: 'Luyện tập nhẹ', icon: Icons.alarm_on_rounded, color: Colors.lightBlue),
    DurationOption(minutes: 15, title: '15 phút', label: 'Tiêu chuẩn', icon: Icons.hourglass_empty_rounded, color: Colors.indigo),
    DurationOption(minutes: 30, title: '30 phút', label: 'Chuyên sâu', icon: Icons.hourglass_full_rounded, color: Colors.purple),
    DurationOption(minutes: 60, title: '60 phút', label: 'Thử thách bền bỉ', icon: Icons.speed_rounded, color: Colors.pinkAccent),
  ];

  @override
  void initState() {
    super.initState();
    _loadPreferences();
    _searchController.addListener(() {
      setState(() {
        _searchQuery = _searchController.text.trim();
      });
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadPreferences() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      setState(() {
        _favoriteIds = prefs.getStringList('roleplay_favorites') ?? [];
        _recentIds = prefs.getStringList('roleplay_recents') ?? [];
        
        _selectedLevel = prefs.getString('roleplay_last_level') ?? 'B1';
        _selectedDuration = prefs.getInt('roleplay_last_duration') ?? 15;
        
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _toggleFavorite(String topicId) async {
    final updatedFavorites = List<String>.from(_favoriteIds);
    if (updatedFavorites.contains(topicId)) {
      updatedFavorites.remove(topicId);
    } else {
      updatedFavorites.add(topicId);
    }

    setState(() {
      _favoriteIds = updatedFavorites;
    });

    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('roleplay_favorites', updatedFavorites);
  }

  Future<void> _addToRecent(String topicId) async {
    final updatedRecents = List<String>.from(_recentIds);
    updatedRecents.remove(topicId);
    updatedRecents.insert(0, topicId);
    
    if (updatedRecents.length > 8) {
      updatedRecents.removeLast();
    }

    setState(() {
      _recentIds = updatedRecents;
    });

    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('roleplay_recents', updatedRecents);
  }

  Future<void> _clearRecents() async {
    setState(() {
      _recentIds = [];
    });
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('roleplay_recents');
  }

  List<RoleplayTopic> _getFilteredTopics() {
    List<RoleplayTopic> baseTopics = [];
    
    switch (_selectedFilter) {
      case TopicFilter.all:
        baseTopics = _allTopics;
        break;
      case TopicFilter.favorites:
        baseTopics = _allTopics.where((t) => _favoriteIds.contains(t.id)).toList();
        break;
      case TopicFilter.recents:
        baseTopics = _recentIds
            .map((id) => _allTopics.firstWhere((t) => t.id == id, orElse: () => _allTopics.first))
            .toList();
        break;
    }

    if (_searchQuery.isEmpty) return baseTopics;

    final query = _searchQuery.toLowerCase();
    return baseTopics.where((t) {
      return t.title.toLowerCase().contains(query) || 
             t.englishTitle.toLowerCase().contains(query);
    }).toList();
  }

  void _handleBackPress() {
    if (_currentStep > 0) {
      setState(() {
        _currentStep--;
      });
    } else {
      context.pop();
    }
  }

  Future<void> _startLearning() async {
    if (_selectedTopic == null || _selectedLevel == null || _selectedDuration == null) return;

    setState(() {
      _isSubmitting = true;
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('roleplay_last_level', _selectedLevel!);
      await prefs.setInt('roleplay_last_duration', _selectedDuration!);
      await _addToRecent(_selectedTopic!.id);

      await ref.read(learnServiceProvider).updatePreferences(
        dailyTimeGoalMinutes: _selectedDuration!,
        targetLevel: _selectedLevel!,
      );

      ref.invalidate(learningDashboardProvider);

      if (mounted) {
        final topicString = '${_selectedTopic!.title} (${_selectedTopic!.englishTitle})';
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                Icon(_selectedTopic!.icon, color: Colors.white),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Đang thiết lập giáo án AI... Trình độ: $_selectedLevel - Thời lượng: $_selectedDuration phút.',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            backgroundColor: _selectedTopic!.color,
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );

        context.push('/voice-chat?mode=roleplay&topic=${Uri.encodeComponent(topicString)}&level=$_selectedLevel');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Lỗi đồng bộ dữ liệu: $e. Đang khởi động lớp học...'),
            backgroundColor: Colors.orangeAccent,
            behavior: SnackBarBehavior.floating,
          ),
        );
        
        final topicString = '${_selectedTopic!.title} (${_selectedTopic!.englishTitle})';
        context.push('/voice-chat?mode=roleplay&topic=${Uri.encodeComponent(topicString)}&level=$_selectedLevel');
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  // Generate Learning Objectives based on duration
  List<String> _getLearningObjectives() {
    final minutes = _selectedDuration ?? 15;
    if (minutes <= 5) {
      return [
        '3 từ vựng mới thuộc chủ đề',
        '1 tình huống hội thoại giao tiếp phản xạ nhanh',
        '1 bài roleplay ngắn cùng AI Coach'
      ];
    } else if (minutes <= 10) {
      return [
        '5 từ vựng mới thuộc chủ đề',
        '1 tình huống hội thoại thực tế',
        '2 lỗi phát âm cần được AI chỉnh sửa',
        '1 bài roleplay tiêu chuẩn'
      ];
    } else if (minutes <= 15) {
      return [
        '10 từ vựng mới nâng cao',
        '1 tình huống hội thoại chi tiết',
        '3 lỗi phát âm cần thực hành sửa đổi',
        '1 bài roleplay đầy đủ cùng AI'
      ];
    } else if (minutes <= 30) {
      return [
        '15 từ vựng mới chuyên sâu',
        '2 tình huống hội thoại đàm thoại phức tạp',
        '5 lỗi phát âm cần thực hành chuyên biệt',
        '2 bài roleplay liên hoàn'
      ];
    } else {
      return [
        '25 từ vựng & thành ngữ bản xứ',
        '4 tình huống hội thoại đàm thoại phản biện',
        '8 lỗi phát âm cần kiểm tra sửa sai toàn diện',
        '3 bài roleplay thử thách thực tế'
      ];
    }
  }

  LevelOption _getSelectedLevelOption() {
    return _levels.firstWhere((l) => l.code == _selectedLevel, orElse: () => _levels[2]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          onPressed: _handleBackPress,
        ),
        title: Text(
          _currentStep == 0
              ? 'Thiết lập buổi học 🎭'
              : _currentStep == 1
                  ? 'Chọn trình độ 🎯'
                  : _currentStep == 2
                      ? 'Chọn thời lượng ⏱️'
                      : 'Giáo án hôm nay 📖',
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Premium Wizard Progress Indicator (4 Steps)
                _buildWizardProgress(),
                const SizedBox(height: 8),

                // Wizard Steps Content
                Expanded(
                  child: IndexedStack(
                    index: _currentStep,
                    children: [
                      _buildStepSelectTopic(),
                      _buildStepSelectLevel(),
                      _buildStepSelectDuration(),
                      _buildStepLessonPlan(),
                    ],
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildWizardProgress() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: Row(
        children: List.generate(4, (index) {
          final isCompleted = index < _currentStep;
          final isActive = index == _currentStep;
          
          return Expanded(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 350),
              height: 5,
              margin: EdgeInsets.only(
                right: index < 3 ? 8.0 : 0.0,
              ),
              decoration: BoxDecoration(
                color: isCompleted
                    ? AppColors.primary
                    : isActive
                        ? AppColors.primary.withOpacity(0.8)
                        : Colors.white.withOpacity(0.1),
                borderRadius: BorderRadius.circular(3),
                boxShadow: isActive ? [
                  BoxShadow(
                    color: AppColors.primary.withOpacity(0.5),
                    blurRadius: 6,
                    spreadRadius: 1,
                  )
                ] : null,
              ),
            ),
          );
        }),
      ),
    );
  }

  // STEP 1: SELECT TOPIC
  Widget _buildStepSelectTopic() {
    final filteredTopics = _getFilteredTopics();

    return Column(
      children: [
        // Search Bar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white.withOpacity(0.08)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.2),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                )
              ],
            ),
            child: TextField(
              controller: _searchController,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'Tìm kiếm chủ đề (Ví dụ: Nấu ăn, Travel...)',
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.35), fontSize: 14),
                prefixIcon: Icon(Icons.search_rounded, color: Colors.white.withOpacity(0.5)),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear_rounded, color: Colors.white54),
                        onPressed: () => _searchController.clear(),
                      )
                    : null,
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
        ),

        // Filter tabs (Chips)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
          child: Row(
            children: [
              _buildFilterChip('Tất cả', TopicFilter.all, Icons.grid_view_rounded),
              const SizedBox(width: 8),
              _buildFilterChip('Yêu thích', TopicFilter.favorites, Icons.favorite_rounded),
              const SizedBox(width: 8),
              _buildFilterChip('Gần đây', TopicFilter.recents, Icons.history_rounded),
            ],
          ),
        ),

        // Clear Recents button
        if (_selectedFilter == TopicFilter.recents && _recentIds.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton.icon(
                  onPressed: _clearRecents,
                  icon: const Icon(Icons.delete_sweep_rounded, size: 16, color: AppColors.textSecondary),
                  label: const Text(
                    'Xóa lịch sử',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                  ),
                ),
              ],
            ),
          ),

        const SizedBox(height: 12),

        // Grid of Topics
        Expanded(
          child: filteredTopics.isEmpty
              ? _buildEmptyState()
              : GridView.builder(
                  padding: const EdgeInsets.only(left: 20, right: 20, bottom: 40),
                  physics: const BouncingScrollPhysics(),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                    childAspectRatio: 1.15,
                  ),
                  itemCount: filteredTopics.length,
                  itemBuilder: (context, index) {
                    final topic = filteredTopics[index];
                    final isFav = _favoriteIds.contains(topic.id);
                    
                    return _buildTopicCard(topic, isFav);
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildFilterChip(String label, TopicFilter filter, IconData icon) {
    final isSelected = _selectedFilter == filter;
    final activeColor = AppColors.primary;

    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() {
            _selectedFilter = filter;
          });
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isSelected ? activeColor.withOpacity(0.15) : AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? activeColor.withOpacity(0.4) : Colors.white.withOpacity(0.05),
              width: 1.2,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 16,
                color: isSelected ? activeColor : AppColors.textSecondary,
              ),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  color: isSelected ? Colors.white : AppColors.textSecondary,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTopicCard(RoleplayTopic topic, bool isFav) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: Colors.white.withOpacity(0.04),
          width: 1,
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: () {
              setState(() {
                _selectedTopic = topic;
                _currentStep = 1; // Transition to Step 2
              });
            },
            child: Stack(
              children: [
                Positioned(
                  right: -10,
                  bottom: -10,
                  child: Icon(
                    topic.icon,
                    size: 80,
                    color: topic.color.withOpacity(0.04),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: topic.color.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Icon(
                              topic.icon,
                              color: topic.color,
                              size: 24,
                            ),
                          ),
                          Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: () => _toggleFavorite(topic.id),
                              borderRadius: BorderRadius.circular(20),
                              child: Container(
                                padding: const EdgeInsets.all(6),
                                child: Icon(
                                  isFav ? Icons.favorite_rounded : Icons.favorite_outline_rounded,
                                  color: isFav ? Colors.redAccent : Colors.white24,
                                  size: 20,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            topic.title,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 2),
                          Text(
                            topic.englishTitle,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.4),
                              fontSize: 12,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    String message = 'Không tìm thấy chủ đề nào!';
    IconData icon = Icons.search_off_rounded;

    if (_selectedFilter == TopicFilter.favorites) {
      message = 'Bạn chưa có chủ đề yêu thích nào.\nHãy nhấn tim các chủ đề bạn thích nhé!';
      icon = Icons.favorite_border_rounded;
    } else if (_selectedFilter == TopicFilter.recents) {
      message = 'Chưa có lịch sử học gần đây.\nHãy chọn một chủ đề để bắt đầu!';
      icon = Icons.history_toggle_off_rounded;
    }

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 60,
              color: Colors.white.withOpacity(0.15),
            ),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.4),
                fontSize: 14,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // STEP 2: SELECT LEVEL
  Widget _buildStepSelectLevel() {
    return FadeIn(
      duration: const Duration(milliseconds: 300),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Text(
              'Chủ đề đã chọn: ${_selectedTopic?.title ?? ""}',
              style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
          ),
          const Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
            child: Text(
              'Bạn muốn luyện tập ở trình độ nào? 🎯',
              style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 40),
              physics: const BouncingScrollPhysics(),
              itemCount: _levels.length,
              itemBuilder: (context, index) {
                final level = _levels[index];
                final isSelected = _selectedLevel == level.code;
                
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12.0),
                  child: Container(
                    decoration: BoxDecoration(
                      color: isSelected ? level.color.withOpacity(0.08) : AppColors.surface,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: isSelected ? level.color.withOpacity(0.5) : Colors.white.withOpacity(0.04),
                        width: isSelected ? 1.5 : 1.0,
                      ),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: () {
                            setState(() {
                              _selectedLevel = level.code;
                              _currentStep = 2; // Transition to Step 3
                            });
                          },
                          child: Padding(
                            padding: const EdgeInsets.all(16.0),
                            child: Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(10),
                                  decoration: BoxDecoration(
                                    color: level.color.withOpacity(0.12),
                                    shape: BoxShape.circle,
                                  ),
                                  child: Icon(
                                    level.icon,
                                    color: level.color,
                                    size: 24,
                                  ),
                                ),
                                const SizedBox(width: 16),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        level.title,
                                        style: TextStyle(
                                          color: isSelected ? level.color : Colors.white,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 15,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        level.description,
                                        style: TextStyle(
                                          color: Colors.white.withOpacity(0.4),
                                          fontSize: 12,
                                          height: 1.3,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                Icon(
                                  Icons.chevron_right_rounded,
                                  color: isSelected ? level.color : Colors.white24,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
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

  // STEP 3: SELECT DURATION
  Widget _buildStepSelectDuration() {
    return FadeIn(
      duration: const Duration(milliseconds: 300),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Text(
              'Chủ đề: ${_selectedTopic?.title ?? ""}  •  Trình độ: ${_selectedLevel ?? ""}',
              style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
          ),
          const Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
            child: Text(
              'Thiết lập thời lượng luyện tập ⏱️',
              style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: GridView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 1.25,
              ),
              itemCount: _durations.length,
              itemBuilder: (context, index) {
                final duration = _durations[index];
                final isSelected = _selectedDuration == duration.minutes;
                
                return Container(
                  decoration: BoxDecoration(
                    color: isSelected ? duration.color.withOpacity(0.08) : AppColors.surface,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: isSelected ? duration.color.withOpacity(0.5) : Colors.white.withOpacity(0.04),
                      width: isSelected ? 1.5 : 1.0,
                    ),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(20),
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: () {
                          setState(() {
                            _selectedDuration = duration.minutes;
                            _currentStep = 3; // Transition to Step 4 (Lesson Plan)
                          });
                        },
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(6),
                                    decoration: BoxDecoration(
                                      color: duration.color.withOpacity(0.12),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Icon(
                                      duration.icon,
                                      color: duration.color,
                                      size: 20,
                                    ),
                                  ),
                                  if (isSelected)
                                    Icon(
                                      Icons.check_circle_rounded,
                                      color: duration.color,
                                      size: 20,
                                    ),
                                ],
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    duration.title,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 16,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    duration.label,
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.4),
                                      fontSize: 11,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
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

  // STEP 4: LESSON PLAN
  Widget _buildStepLessonPlan() {
    final objectives = _getLearningObjectives();
    final levelOpt = _getSelectedLevelOption();

    return FadeInUp(
      duration: const Duration(milliseconds: 400),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Text(
              'Hôm nay chúng ta sẽ học gì? 📖',
              style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              physics: const BouncingScrollPhysics(),
              child: Column(
                children: [
                  // Lesson Plan Card
                  Container(
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(
                        color: Colors.white.withOpacity(0.06),
                        width: 1.2,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.3),
                          blurRadius: 15,
                          offset: const Offset(0, 8),
                        )
                      ],
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Header: Icon & Title
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: (_selectedTopic?.color ?? AppColors.primary).withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: Icon(
                                  _selectedTopic?.icon ?? Icons.class_rounded,
                                  color: _selectedTopic?.color ?? AppColors.primary,
                                  size: 32,
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'GIÁO ÁN NHẬP VAI',
                                      style: TextStyle(
                                        color: AppColors.primary,
                                        fontSize: 11,
                                        fontWeight: FontWeight.w800,
                                        letterSpacing: 1.5,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      _selectedTopic?.title ?? '',
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 20,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    Text(
                                      'Topic: ${_selectedTopic?.englishTitle ?? ""}',
                                      style: TextStyle(
                                        color: Colors.white.withOpacity(0.35),
                                        fontSize: 13,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          
                          const SizedBox(height: 24),
                          
                          // Difficulty & Time Badges
                          Row(
                            children: [
                              // Difficulty Badge
                              Expanded(
                                child: Container(
                                  padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                                  decoration: BoxDecoration(
                                    color: levelOpt.color.withOpacity(0.08),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: levelOpt.color.withOpacity(0.15),
                                    ),
                                  ),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(levelOpt.icon, color: levelOpt.color, size: 16),
                                      const SizedBox(width: 8),
                                      Flexible(
                                        child: Text(
                                          levelOpt.name,
                                          style: TextStyle(
                                            color: levelOpt.color,
                                            fontWeight: FontWeight.bold,
                                            fontSize: 12,
                                          ),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              
                              // Estimated Time Badge
                              Expanded(
                                child: Container(
                                  padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                                  decoration: BoxDecoration(
                                    color: Colors.blue.withOpacity(0.08),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: Colors.blue.withOpacity(0.15),
                                    ),
                                  ),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      const Icon(Icons.timer_rounded, color: Colors.blue, size: 16),
                                      const SizedBox(width: 8),
                                      Text(
                                        '$_selectedDuration phút',
                                        style: const TextStyle(
                                          color: Colors.blue,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 12,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                          
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 20),
                            child: Divider(
                              color: Colors.white.withOpacity(0.06),
                              height: 1,
                            ),
                          ),
                          
                          // Learning Objectives Section
                          const Text(
                            'Mục tiêu học tập:',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                            ),
                          ),
                          const SizedBox(height: 12),
                          
                          // Objectives list
                          ...objectives.map((obj) => Padding(
                            padding: const EdgeInsets.only(bottom: 10.0),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(
                                  Icons.check_circle_outline_rounded,
                                  color: Colors.greenAccent,
                                  size: 18,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    obj,
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.85),
                                      fontSize: 14,
                                      height: 1.3,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          )).toList(),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          
          // Action button bottom
          Padding(
            padding: const EdgeInsets.only(left: 20, right: 20, bottom: 40, top: 12),
            child: SizedBox(
              width: double.infinity,
              height: 56,
              child: Container(
                decoration: BoxDecoration(
                  gradient: AppColors.primaryGradient,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withOpacity(0.3),
                      blurRadius: 12,
                      offset: const Offset(0, 6),
                    )
                  ],
                ),
                child: ElevatedButton(
                  onPressed: _isSubmitting ? null : _startLearning,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.transparent,
                    shadowColor: Colors.transparent,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: _isSubmitting
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              'Bắt đầu học',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
