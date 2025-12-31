import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/user.dart';

/// Authentication credentials
class LoginCredentials {
  final String email;
  final String password;

  const LoginCredentials({
    required this.email,
    required this.password,
  });
}

/// Registration data
class RegisterData {
  final String username;
  final String email;
  final String password;

  const RegisterData({
    required this.username,
    required this.email,
    required this.password,
  });
}

/// Authentication tokens
class AuthTokens {
  final String accessToken;
  final String refreshToken;

  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
  });
}

/// Abstract auth repository - contract for authentication operations
abstract class AuthRepository {
  /// Login with credentials
  Future<Either<Failure, (User, AuthTokens)>> login(LoginCredentials credentials);

  /// Register a new user
  Future<Either<Failure, User>> register(RegisterData data);

  /// Logout current user
  Future<Either<Failure, void>> logout();

  /// Get current authenticated user
  Future<Either<Failure, User>> getCurrentUser();

  /// Refresh authentication tokens
  Future<Either<Failure, AuthTokens>> refreshToken(String refreshToken);

  /// Check if user is authenticated
  Future<bool> isAuthenticated();

  /// Get stored access token
  Future<String?> getAccessToken();

  /// Clear stored tokens
  Future<void> clearTokens();
}

