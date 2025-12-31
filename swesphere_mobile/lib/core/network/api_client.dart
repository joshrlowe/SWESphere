import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api_interceptors.dart';

/// API Configuration
abstract class ApiConfig {
  /// Base URL for the API
  /// Change this to your production URL
  static const String baseUrl = 'http://localhost:8000';
  
  /// API version prefix
  static const String apiPrefix = '/api/v1';
  
  /// Full API URL
  static String get apiUrl => '$baseUrl$apiPrefix';
  
  /// Connection timeout
  static const Duration connectTimeout = Duration(seconds: 30);
  
  /// Receive timeout
  static const Duration receiveTimeout = Duration(seconds: 30);
}

/// Dio instance provider
final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: ApiConfig.apiUrl,
      connectTimeout: ApiConfig.connectTimeout,
      receiveTimeout: ApiConfig.receiveTimeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ),
  );
  
  final storage = ref.watch(secureStorageProvider);
  
  // Add interceptors
  dio.interceptors.addAll([
    AuthInterceptor(storage: storage, dio: dio),
    ErrorInterceptor(),
    LoggingInterceptor(),
  ]);
  
  return dio;
});

/// API Client wrapper with convenience methods
class ApiClient {
  final Dio _dio;

  ApiClient(this._dio);

  /// GET request
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
    bool skipAuth = false,
  }) {
    return _dio.get<T>(
      path,
      queryParameters: queryParameters,
      options: _mergeOptions(options, skipAuth: skipAuth),
    );
  }

  /// POST request
  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    bool skipAuth = false,
  }) {
    return _dio.post<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: _mergeOptions(options, skipAuth: skipAuth),
    );
  }

  /// PUT request
  Future<Response<T>> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    bool skipAuth = false,
  }) {
    return _dio.put<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: _mergeOptions(options, skipAuth: skipAuth),
    );
  }

  /// PATCH request
  Future<Response<T>> patch<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    bool skipAuth = false,
  }) {
    return _dio.patch<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: _mergeOptions(options, skipAuth: skipAuth),
    );
  }

  /// DELETE request
  Future<Response<T>> delete<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    bool skipAuth = false,
  }) {
    return _dio.delete<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: _mergeOptions(options, skipAuth: skipAuth),
    );
  }

  /// Upload file with multipart form data
  Future<Response<T>> upload<T>(
    String path, {
    required FormData formData,
    ProgressCallback? onSendProgress,
    Options? options,
  }) {
    return _dio.post<T>(
      path,
      data: formData,
      onSendProgress: onSendProgress,
      options: options,
    );
  }

  Options _mergeOptions(Options? options, {bool skipAuth = false}) {
    final extra = <String, dynamic>{
      if (skipAuth) 'skipAuth': true,
    };
    
    if (options != null) {
      return options.copyWith(
        extra: {...?options.extra, ...extra},
      );
    }
    
    return Options(extra: extra);
  }
}

/// API Client provider
final apiClientProvider = Provider<ApiClient>((ref) {
  final dio = ref.watch(dioProvider);
  return ApiClient(dio);
});

