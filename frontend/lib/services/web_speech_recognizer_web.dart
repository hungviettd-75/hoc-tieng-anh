import 'dart:html' as html;
import 'dart:js_util' as js_util;
import 'dart:js' as js;

/// Web implementation sử dụng JavaScript interop thuần túy.
/// Hoàn toàn tránh dart:html SpeechRecognition class để không bị bug TypeError.
class WebSpeechRecognizer {
  dynamic _recognition;
  void Function(String text)? onResult;
  void Function(String status)? onStatus;
  void Function()? onEnd;
  bool _isStarted = false;

  Future<bool> initialize() async {
    return true; // Khởi tạo thực tế sẽ nằm trong start()
  }

  void start({String locale = 'en-US'}) {
    try {
      // 1. Dọn dẹp phiên cũ nếu có
      dispose();

      // 2. Tạo đối tượng mới hoàn toàn để tránh 'InvalidStateError'
      final speechRecClass = js_util.getProperty(html.window, 'SpeechRecognition') ??
          js_util.getProperty(html.window, 'webkitSpeechRecognition');
      
      if (speechRecClass == null) {
        onStatus?.call('error: not supported');
        return;
      }
      
      _recognition = js_util.callConstructor(speechRecClass, []);
      
      // 3. Cấu hình
      js_util.setProperty(_recognition, 'continuous', false); // Dùng false + auto-restart bền bỉ hơn
      js_util.setProperty(_recognition, 'interimResults', true);
      js_util.setProperty(_recognition, 'lang', locale);

      // 4. Thiết lập Handlers
      js_util.setProperty(_recognition, 'onresult', js.allowInterop((dynamic event) {
        try {
          final results = js_util.getProperty(event, 'results');
          final length = js_util.getProperty(results, 'length') as int;
          String transcript = '';
          for (int i = 0; i < length; i++) {
            final result = js_util.callMethod(results, 'item', [i]);
            final alt = js_util.callMethod(result, 'item', [0]);
            transcript += js_util.getProperty(alt, 'transcript') as String;
          }
          onResult?.call(transcript);
        } catch (_) {}
      }));

      js_util.setProperty(_recognition, 'onerror', js.allowInterop((dynamic event) {
        final error = js_util.getProperty(event, 'error');
        print('WebSpeechRecognizer Error: $error');
        _isStarted = false;
        onStatus?.call('error: $error');
      }));

      js_util.setProperty(_recognition, 'onend', js.allowInterop((dynamic event) {
        if (_isStarted) {
          _isStarted = false;
          onEnd?.call();
        }
      }));

      // 5. Kích hoạt
      js_util.callMethod(_recognition, 'start', []);
      _isStarted = true;
      onStatus?.call('listening');
    } catch (e) {
      print('WebSpeechRecognizer Exception: $e');
      _isStarted = false;
      onStatus?.call('error: $e');
    }
  }

  void stop() {
    if (_recognition != null && _isStarted) {
      _isStarted = false; // Chặn onEnd tự kích hoạt lại
      try {
        js_util.callMethod(_recognition, 'stop', []);
      } catch (_) {}
    }
  }

  void dispose() {
    if (_recognition != null) {
      _isStarted = false;
      try {
        js_util.callMethod(_recognition, 'abort', []);
      } catch (_) {}
      _recognition = null;
    }
  }
}
