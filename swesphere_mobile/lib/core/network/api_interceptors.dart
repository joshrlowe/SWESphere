import 'dart:developer' as developer;
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Storage keys for tokens
abstract class StorageKeys {
  static const String accessToken = 'access_token';
  static const String refreshToken = 'refresh_token';
}

/// Secure storage provider
final secureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
  );
});

/// Auth interceptor for adding tokens and handling refresh
class AuthInterceptor extends Interceptor {
  final FlutterSecureStorage _storage;
  final Dio _dio;

  AuthInterceptor({
    required FlutterSecureStorage storage,
    required Dio dio,
  })  : _storage = storage,
        _dio = dio;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Skip auth for public endpoints
    if (options.extra['skipAuth'] == true) {
      return handler.next(options);
    }

    final accessToken = await _storage.read(key: StorageKeys.accessToken);
    if (accessToken != null) {
      options.headers['Authorization'] = 'Bearer $accessToken';
    }

    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    // Handle 401 - try to refresh token
    if (err.response?.statusCode == 401) {
      final refreshToken = await _storage.read(key: StorageKeys.refreshToken);
      
      if (refreshToken != null && !err.requestOptions.path.contains('/refresh')) {
        try {
          final refreshed = await _refreshToken(refreshToken);
          if (refreshed) {
            // Retry the failed request
            final response = await _retryRequest(err.requestOptions);
            return handler.resolve(response);
          }
        } catch (_) {
          // Refresh failed, clear tokens
          await _clearTokens();
        }
      }
    }

    handler.next(err);
  }

  Future<bool> _refreshToken(String refreshToken) async {
    try {
      final response = await _dio.post(
        '/api/v1/auth/refresh',
        data: {'refresh_token': refreshToken},
        options: Options(extra: {'skipAuth': true}),
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        await _storage.write(
          key: StorageKeys.accessToken,
          value: data['access_token'] as String,
        );
        await _storage.write(
          key: StorageKeys.refreshToken,
          value: data['refresh_token'] as String,
        );
        return true;
      }
    } catch (e) {
      developer.log('Token refresh failed: $e');
    }
    return false;
  }

  Future<Response<dynamic>> _retryRequest(RequestOptions requestOptions) async {
    final accessToken = await _storage.read(key: StorageKeys.accessToken);
    
    final options = Options(
      method: requestOptions.method,
      headers: {
        ...requestOptions.headers,
        'Authorization': 'Bearer $accessToken',
      },
    );

    return _dio.request(
      requestOptions.path,
      data: requestOptions.data,
      queryParameters: requestOptions.queryParameters,
      options: options,
    );
  }

  Future<void> _clearTokens() async {
    await _storage.delete(key: StorageKeys.accessToken);
    await _storage.delete(key: StorageKeys.refreshToken);
  }
}

/// Logging interceptor for debugging
class LoggingInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    developer.log(
      '🌐 REQUEST[${options.method}] => PATH: ${options.path}',
      name: 'API',
    );
    if (options.data != null) {
      developer.log('📦 DATA: ${options.data}', name: 'API');
    }
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    developer.log(
      '✅ RESPONSE[${response.statusCode}] => PATH: ${response.requestOptions.path}',
      name: 'API',
    );
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    developer.log(
      '❌ ERROR[${err.response?.statusCode}] => PATH: ${err.requestOptions.path}',
      name: 'API',
    );
    developer.log('📛 MESSAGE: ${err.message}', name: 'API');
    handler.next(err);
  }
}

/// Error handling interceptor
class ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    // Transform Dio errors into app-specific errors
    final response = err.response;
    
    if (response != null) {
      final data = response.data;
      String? message;
      
      if (data is Map<String, dynamic>) {
        message = data['detail'] as String? ?? data['message'] as String?;
      }
      
      // Create a more descriptive error
      final error = DioException(
        requestOptions: err.requestOptions,
        response: err.response,
        type: err.type,
        error: message ?? err.message,
        message: message ?? err.message,
      );
      
      handler.next(error);
    } else {
      handler.next(err);
    }
  }
}

