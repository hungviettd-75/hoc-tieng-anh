import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:animate_do/animate_do.dart';
import '../providers/speaking_provider.dart';
import '../widgets/practice_card_widget.dart';
import '../../models/pronunciation_models.dart';

class IELTSPage extends ConsumerStatefulWidget {
  const IELTSPage({super.key});

  @override
  ConsumerState<IELTSPage> createState() => _IELTSPageState();
}

class _IELTSPageState extends ConsumerState<IELTSPage> {
  String _selectedCategory = 'all';

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(speakingProvider.notifier).loadSentences();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(speakingProvider);
    
    // Get all IELTS sentences
    final allIelts = state.sentences.where((s) => s.category.toLowerCase().startsWith('ielts')).toList();
    
    // Filter based on selection
    List<PracticeSentence> filteredSentences;
    if (_selectedCategory == 'all') {
      filteredSentences = allIelts;
    } else {
      filteredSentences = allIelts.where((s) => s.category.toLowerCase() == _selectedCategory).toList();
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        slivers: [
          _buildAppBar(context),
          
          _buildHeader(),

          // Filter Buttons Section
          SliverToBoxAdapter(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  _buildFilterButton('Tất cả', 'all'),
                  _buildFilterButton('Part 1: Giới thiệu & Phỏng vấn', 'ielts_p1'),
                  _buildFilterButton('Part 2: Luyện nói cá nhân (Độc thoại)', 'ielts_p2'),
                  _buildFilterButton('Part 3: Thảo luận hai chiều', 'ielts_p3'),
                  _buildFilterButton('Part 4: Chủ đề học thuật nâng cao', 'ielts_p4'),
                ],
              ),
            ),
          ),

          const SliverToBoxAdapter(child: SizedBox(height: 8)),

          // Sentence List
          _buildSentenceList(filteredSentences),
          
          const SliverToBoxAdapter(child: SizedBox(height: 100)),
        ],
      ),
    );
  }

  Widget _buildFilterButton(String label, String category) {
    final isSelected = _selectedCategory == category;
    return Padding(
      padding: const EdgeInsets.only(right: 12),
      child: InkWell(
        onTap: () => setState(() => _selectedCategory = category),
        borderRadius: BorderRadius.circular(12),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          decoration: BoxDecoration(
            color: isSelected ? Colors.purple : Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? Colors.purpleAccent : Colors.white12,
              width: 1,
            ),
            boxShadow: isSelected ? [
              BoxShadow(
                color: Colors.purple.withOpacity(0.3),
                blurRadius: 8,
                offset: const Offset(0, 4),
              )
            ] : null,
          ),
          child: Text(
            label,
            style: TextStyle(
              color: isSelected ? Colors.white : Colors.white70,
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 10),
        child: FadeInDown(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.purple.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  'IELTS PREP',
                  style: TextStyle(color: Colors.purpleAccent, fontWeight: FontWeight.bold, fontSize: 10),
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Làm chủ kỹ năng Nói',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSentenceList(List<PracticeSentence> sentences) {
    if (sentences.isEmpty) {
      return const SliverToBoxAdapter(
        child: Padding(
          padding: EdgeInsets.all(40.0),
          child: Center(
            child: Column(
              children: [
                CircularProgressIndicator(color: Colors.purpleAccent),
                SizedBox(height: 16),
                Text('Đang tải câu hỏi...', style: TextStyle(color: Colors.white54)),
              ],
            ),
          ),
        ),
      );
    }
    return SliverPadding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      sliver: SliverList(
        delegate: SliverChildBuilderDelegate(
          (context, index) {
            final sentence = sentences[index];
            return FadeInUp(
              delay: Duration(milliseconds: 30 * index),
              child: Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: PracticeCardWidget(
                  sentence: sentence,
                  onTap: () => context.push('/speaking/practice', extra: sentence),
                  onListen: () => ref.read(speakingProvider.notifier).playReference(sentence.text),
                ),
              ),
            );
          },
          childCount: sentences.length,
        ),
      ),
    );
  }

  Widget _buildAppBar(BuildContext context) {
    return SliverAppBar(
      pinned: true,
      backgroundColor: AppColors.background,
      leading: IconButton(
        icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
        onPressed: () => Navigator.of(context).canPop() ? context.pop() : context.go('/'),
      ),
      title: const Text('Luyện thi IELTS', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
      centerTitle: true,
    );
  }
}
