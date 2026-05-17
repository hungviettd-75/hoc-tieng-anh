/// Stub implementation cho mobile platforms (Android/iOS)
/// Trên mobile, sẽ sử dụng speech_to_text package thay thế
class WebSpeechRecognizer {
  void Function(String text)? onResult;
  void Function(String status)? onStatus;
  void Function()? onEnd;

  Future<bool> initialize() async => false;

  void start({String locale = 'en-US'}) {}

  void stop() {}

  void dispose() {}
}
