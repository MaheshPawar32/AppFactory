/// Guards an async action against concurrent duplicate invocation.
/// UI layers should still show progress and handle errors visibly.
final class SafeAction {
  bool _running = false;

  bool get isRunning => _running;

  Future<R?> run<R>(Future<R> Function() action) async {
    if (_running) return null;
    _running = true;
    try {
      return await action();
    } finally {
      _running = false;
    }
  }
}
