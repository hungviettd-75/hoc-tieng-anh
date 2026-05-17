import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ai_english_coach/theme/app_colors.dart';
import 'package:ai_english_coach/features/auth/presentation/providers/auth_provider.dart';

class RegisterPage extends ConsumerStatefulWidget {
  const RegisterPage({super.key});

  @override
  ConsumerState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends ConsumerState<RegisterPage> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    ref.listen(authProvider, (previous, next) {
      if (next.error != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(next.error!), backgroundColor: Colors.redAccent),
        );
      }
      if (next.user != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Đăng ký thành công! Chào mừng bạn!'), backgroundColor: Colors.green),
        );
        context.go('/');
      }
    });

    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, elevation: 0),
      extendBodyBehindAppBar: true,
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topRight,
            end: Alignment.bottomLeft,
            colors: [
              AppColors.background,
              AppColors.secondary.withOpacity(0.1),
            ],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 30),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 20),
                  const Text(
                    'Tạo tài khoản',
                    style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Bắt đầu hành trình học tiếng Anh ngay hôm nay',
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                  const SizedBox(height: 40),
                  _buildTextField(
                    controller: _nameController,
                    hint: 'Họ và tên',
                    icon: Icons.person_outline,
                  ),
                  const SizedBox(height: 20),
                  _buildTextField(
                    controller: _emailController,
                    hint: 'Email',
                    icon: Icons.email_outlined,
                  ),
                  const SizedBox(height: 20),
                  _buildTextField(
                    controller: _passwordController,
                    hint: 'Mật khẩu',
                    icon: Icons.lock_outline,
                    isPassword: true,
                  ),
                  const SizedBox(height: 40),
                  ElevatedButton(
                    onPressed: authState.isLoading ? null : _handleRegister,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
                    ),
                    child: authState.isLoading
                        ? const CircularProgressIndicator(color: Colors.white)
                        : const Text('Đăng ký', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text("Đã có tài khoản?", style: TextStyle(color: AppColors.textSecondary)),
                      TextButton(
                        onPressed: () => context.pop(),
                        child: const Text('Đăng nhập', style: TextStyle(color: AppColors.primary)),
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
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    bool isPassword = false,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(15),
      ),
      child: TextFormField(
        controller: controller,
        obscureText: isPassword,
        style: const TextStyle(color: Colors.white),
        decoration: InputDecoration(
          prefixIcon: Icon(icon, color: AppColors.textSecondary),
          hintText: hint,
          hintStyle: const TextStyle(color: AppColors.textSecondary),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.all(20),
        ),
        validator: (value) => value == null || value.isEmpty ? 'Please enter $hint' : null,
      ),
    );
  }

  void _handleRegister() {
    if (_formKey.currentState!.validate()) {
      ref.read(authProvider.notifier).register(
            _emailController.text,
            _passwordController.text,
            _nameController.text,
          );
    }
  }
}
