// Conditional export: sử dụng dart:html trên web, stub trên mobile
export 'web_speech_recognizer_stub.dart'
    if (dart.library.html) 'web_speech_recognizer_web.dart';
