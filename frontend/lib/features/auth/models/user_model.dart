class UserModel {
  final int id;
  final String email;
  final String fullName;
  final String level;
  final bool isVerified;

  UserModel({
    required this.id,
    required this.email,
    required this.fullName,
    required this.level,
    required this.isVerified,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'],
      email: json['email'],
      fullName: json['full_name'] ?? '',
      level: json['level'] ?? 'A1',
      isVerified: json['is_verified'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      'level': level,
      'is_verified': isVerified,
    };
  }
}
