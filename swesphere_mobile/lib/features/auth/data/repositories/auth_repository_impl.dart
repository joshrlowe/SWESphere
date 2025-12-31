import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';

import '../../../../core/error/failures.dart';
import '../../domain/entities/user.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/auth_local_datasource.dart';
import '../datasources/auth_remote_datasource.dart';
import '../models/user_model.dart';

/// Implementation of AuthRepository
class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource remoteDataSource;
  final AuthLocalDataSource localDataSource;

  AuthRepositoryImpl({
    required this.remoteDataSource,
    required this.localDataSource,
  });

  @override
  Future<Either<Failure, (User, AuthTokens)>> login(
    LoginCredentials credentials,
  ) async {
    try {
      final response = await remoteDataSource.login(
        LoginRequest(
          username: credentials.email,
          password: credentials.password,
        ),
      );

      final loginResponse = LoginResponse.fromJson(
        response.data as Map<String, dynamic>,
      );

      // Save tokens
      await localDataSource.saveAccessToken(loginResponse.accessToken);
      await localDataSource.saveRefreshToken(loginResponse.refreshToken);

      // Get user from response or fetch
      User user;
      if (loginResponse.user != null) {
        user = loginResponse.user!.toEntity();
        await localDataSource.cacheUser(loginResponse.user!);
      } else {
        // Fetch user from API
        final userResult = await getCurrentUser();
        user = userResult.fold(
          (failure) => throw Exception(failure.message),
          (fetchedUser) => fetchedUser,
        );
      }

      final tokens = AuthTokens(
        accessToken: loginResponse.accessToken,
        refreshToken: loginResponse.refreshToken,
      );

      return Right((user, tokens));
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, User>> register(RegisterData data) async {
    try {
      await remoteDataSource.register(
        RegisterRequest(
          username: data.username,
          email: data.email,
          password: data.password,
        ),
      );

      // Auto-login after registration
      final loginResult = await login(
        LoginCredentials(
          email: data.email,
          password: data.password,
        ),
      );

      return loginResult.map((tuple) => tuple.$1);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> logout() async {
    try {
      await remoteDataSource.logout();
    } catch (_) {
      // Ignore logout errors - we'll clear local state anyway
    }

    await localDataSource.clearTokens();
    await localDataSource.clearCachedUser();
    return const Right(null);
  }

  @override
  Future<Either<Failure, User>> getCurrentUser() async {
    try {
      final response = await remoteDataSource.getCurrentUser();
      final userModel = UserModel.fromJson(
        response.data as Map<String, dynamic>,
      );

      await localDataSource.cacheUser(userModel);
      return Right(userModel.toEntity());
    } on DioException catch (e) {
      // Try to get cached user on network error
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        final cachedUser = await localDataSource.getCachedUser();
        if (cachedUser != null) {
          return Right(cachedUser.toEntity());
        }
      }
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, AuthTokens>> refreshToken(String refreshToken) async {
    try {
      final response = await remoteDataSource.refreshToken({
        'refresh_token': refreshToken,
      });

      final refreshResponse = RefreshResponse.fromJson(
        response.data as Map<String, dynamic>,
      );

      await localDataSource.saveAccessToken(refreshResponse.accessToken);
      await localDataSource.saveRefreshToken(refreshResponse.refreshToken);

      return Right(AuthTokens(
        accessToken: refreshResponse.accessToken,
        refreshToken: refreshResponse.refreshToken,
      ));
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<bool> isAuthenticated() async {
    return localDataSource.hasTokens();
  }

  @override
  Future<String?> getAccessToken() async {
    return localDataSource.getAccessToken();
  }

  @override
  Future<void> clearTokens() async {
    await localDataSource.clearTokens();
  }

  Failure _handleDioError(DioException e) {
    switch (e.response?.statusCode) {
      case 400:
        final message = _extractErrorMessage(e) ?? 'Bad request';
        return ValidationFailure(message);
      case 401:
        return const AuthFailure('Invalid credentials');
      case 403:
        return const PermissionFailure('Access denied');
      case 404:
        return const NotFoundFailure('User not found');
      case 409:
        return const ValidationFailure('User already exists');
      case 422:
        final message = _extractErrorMessage(e) ?? 'Validation error';
        return ValidationFailure(message);
      case 500:
        return const ServerFailure('Server error. Please try again later.');
      default:
        if (e.type == DioExceptionType.connectionError ||
            e.type == DioExceptionType.connectionTimeout) {
          return const NetworkFailure();
        }
        return ServerFailure(e.message ?? 'An error occurred');
    }
  }

  String? _extractErrorMessage(DioException e) {
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      return data['detail'] as String? ?? data['message'] as String?;
    }
    return null;
  }
}

