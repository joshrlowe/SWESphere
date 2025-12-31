import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_interceptors.dart';
import '../../domain/entities/user.dart';
import '../../data/models/user_model.dart';

part 'auth_provider.g.dart';

/// Authentication state
sealed class AuthState {
  const AuthState();
}

class AuthInitial extends AuthState {
  const AuthInitial();
}

class AuthLoading extends AuthState {
  const AuthLoading();
}

class AuthAuthenticated extends AuthState {
  final User user;
  const AuthAuthenticated(this.user);
}

class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated();
}

class AuthError extends AuthState {
  final String message;
  const AuthError(this.message);
}

/// Extension for pattern matching
extension AuthStateExtension on AuthState {
  T maybeWhen<T>({
    T Function()? initial,
    T Function()? loading,
    T Function(User user)? authenticated,
    T Function()? unauthenticated,
    T Function(String message)? error,
    required T Function() orElse,
  }) {
    return switch (this) {
      AuthInitial() => initial?.call() ?? orElse(),
      AuthLoading() => loading?.call() ?? orElse(),
      AuthAuthenticated(user: final u) => authenticated?.call(u) ?? orElse(),
      AuthUnauthenticated() => unauthenticated?.call() ?? orElse(),
      AuthError(message: final m) => error?.call(m) ?? orElse(),
    };
  }
}

/// Auth state notifier provider
final authStateProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    apiClient: ref.watch(apiClientProvider),
    storage: ref.watch(secureStorageProvider),
  );
});

/// Current user provider
final currentUserProvider = Provider<User?>((ref) {
  final authState = ref.watch(authStateProvider);
  return authState.maybeWhen(
    authenticated: (user) => user,
    orElse: () => null,
  );
});

/// Is authenticated provider
final isAuthenticatedProvider = Provider<bool>((ref) {
  final authState = ref.watch(authStateProvider);
  return authState.maybeWhen(
    authenticated: (_) => true,
    orElse: () => false,
  );
});

/// Auth notifier for managing authentication state
class AuthNotifier extends StateNotifier<AuthState> {
  final ApiClient _apiClient;
  final FlutterSecureStorage _storage;

  AuthNotifier({
    required ApiClient apiClient,
    required FlutterSecureStorage storage,
  })  : _apiClient = apiClient,
        _storage = storage,
        super(const AuthInitial()) {
    _init();
  }

  /// Initialize authentication state
  Future<void> _init() async {
    state = const AuthLoading();

    try {
      final accessToken = await _storage.read(key: StorageKeys.accessToken);
      
      if (accessToken == null) {
        state = const AuthUnauthenticated();
        return;
      }

      // Try to get current user
      final response = await _apiClient.get('/users/me');
      final user = UserModel.fromJson(response.data as Map<String, dynamic>);
      state = AuthAuthenticated(user.toEntity());
    } catch (e) {
      // Token invalid, clear and set unauthenticated
      await _clearTokens();
      state = const AuthUnauthenticated();
    }
  }

  /// Login with email and password
  Future<void> login({
    required String email,
    required String password,
  }) async {
    state = const AuthLoading();

    try {
      final response = await _apiClient.post(
        '/auth/login',
        data: {
          'username': email,
          'password': password,
        },
        skipAuth: true,
      );

      final data = response.data as Map<String, dynamic>;
      final tokens = data['tokens'] as Map<String, dynamic>? ?? data;
      
      // Store tokens
      await _storage.write(
        key: StorageKeys.accessToken,
        value: tokens['access_token'] as String,
      );
      await _storage.write(
        key: StorageKeys.refreshToken,
        value: tokens['refresh_token'] as String,
      );

      // Get user from response or fetch
      final userData = data['user'] as Map<String, dynamic>?;
      if (userData != null) {
        final user = UserModel.fromJson(userData);
        state = AuthAuthenticated(user.toEntity());
      } else {
        // Fetch user
        final userResponse = await _apiClient.get('/users/me');
        final user = UserModel.fromJson(userResponse.data as Map<String, dynamic>);
        state = AuthAuthenticated(user.toEntity());
      }
    } catch (e) {
      state = AuthError(e.toString());
      rethrow;
    }
  }

  /// Register a new user
  Future<void> register({
    required String username,
    required String email,
    required String password,
  }) async {
    state = const AuthLoading();

    try {
      await _apiClient.post(
        '/auth/register',
        data: {
          'username': username,
          'email': email,
          'password': password,
        },
        skipAuth: true,
      );

      // Auto-login after registration
      await login(email: email, password: password);
    } catch (e) {
      state = AuthError(e.toString());
      rethrow;
    }
  }

  /// Logout
  Future<void> logout() async {
    try {
      await _apiClient.post('/auth/logout');
    } catch (_) {
      // Ignore errors
    } finally {
      await _clearTokens();
      state = const AuthUnauthenticated();
    }
  }

  /// Clear stored tokens
  Future<void> _clearTokens() async {
    await _storage.delete(key: StorageKeys.accessToken);
    await _storage.delete(key: StorageKeys.refreshToken);
  }

  /// Update current user
  void updateUser(User user) {
    if (state is AuthAuthenticated) {
      state = AuthAuthenticated(user);
    }
  }
}

