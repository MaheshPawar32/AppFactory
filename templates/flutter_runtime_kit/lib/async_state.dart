/// Immutable async state model suitable for Provider, setState, or other
/// existing state-management choices. It introduces no framework dependency.
sealed class AsyncState<T> {
  const AsyncState();

  const factory AsyncState.idle() = AsyncIdle<T>;
  const factory AsyncState.loading({T? previous}) = AsyncLoading<T>;
  const factory AsyncState.data(T value) = AsyncData<T>;
  const factory AsyncState.error(String message, {T? previous}) = AsyncError<T>;

  T? get previous => switch (this) {
        AsyncLoading<T>(:final previous) => previous,
        AsyncError<T>(:final previous) => previous,
        _ => null,
      };
}

final class AsyncIdle<T> extends AsyncState<T> {
  const AsyncIdle();
}

final class AsyncLoading<T> extends AsyncState<T> {
  const AsyncLoading({this.previous});
  @override
  final T? previous;
}

final class AsyncData<T> extends AsyncState<T> {
  const AsyncData(this.value);
  final T value;
}

final class AsyncError<T> extends AsyncState<T> {
  const AsyncError(this.message, {this.previous});
  final String message;
  @override
  final T? previous;
}
