/// Small, dependency-free result type for expected application outcomes.
sealed class AppResult<T> {
  const AppResult();

  const factory AppResult.success(T value) = AppSuccess<T>;
  const factory AppResult.failure(AppFailure failure) = AppFailureResult<T>;

  R fold<R>({
    required R Function(T value) onSuccess,
    required R Function(AppFailure failure) onFailure,
  }) {
    return switch (this) {
      AppSuccess<T>(:final value) => onSuccess(value),
      AppFailureResult<T>(:final failure) => onFailure(failure),
    };
  }

  bool get isSuccess => this is AppSuccess<T>;
}

final class AppSuccess<T> extends AppResult<T> {
  const AppSuccess(this.value);
  final T value;
}

final class AppFailureResult<T> extends AppResult<T> {
  const AppFailureResult(this.failure);
  final AppFailure failure;
}

/// Safe, user-displayable failure. Keep secrets and raw backend responses out.
final class AppFailure {
  const AppFailure({
    required this.message,
    this.code,
    this.retryable = false,
  });

  final String message;
  final String? code;
  final bool retryable;
}
