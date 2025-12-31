import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/user_model.dart';

part 'auth_remote_datasource.g.dart';

/// Login request body
class LoginRequest {
  final String username;
  final String password;

  LoginRequest({
    required this.username,
    required this.password,
  });

  Map<String, dynamic> toJson() => {
        'username': username,
        'password': password,
      };
}

/// Register request body
class RegisterRequest {
  final String username;
  final String email;
  final String password;

  RegisterRequest({
    required this.username,
    required this.email,
    required this.password,
  });

  Map<String, dynamic> toJson() => {
        'username': username,
        'email': email,
        'password': password,
      };
}

/// Login response
class LoginResponse {
  final String accessToken;
  final String refreshToken;
  final UserModel? user;

  LoginResponse({
    required this.accessToken,
    required this.refreshToken,
    this.user,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    final tokens = json['tokens'] as Map<String, dynamic>? ?? json;
    return LoginResponse(
      accessToken: tokens['access_token'] as String,
      refreshToken: tokens['refresh_token'] as String,
      user: json['user'] != null
          ? UserModel.fromJson(json['user'] as Map<String, dynamic>)
          : null,
    );
  }
}

/// Token refresh response
class RefreshResponse {
  final String accessToken;
  final String refreshToken;

  RefreshResponse({
    required this.accessToken,
    required this.refreshToken,
  });

  factory RefreshResponse.fromJson(Map<String, dynamic> json) {
    return RefreshResponse(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
    );
  }
}

/// Remote data source for authentication
@RestApi()
abstract class AuthRemoteDataSource {
  factory AuthRemoteDataSource(Dio dio, {String baseUrl}) = _AuthRemoteDataSource;

  /// Login with credentials
  @POST('/auth/login')
  Future<HttpResponse<dynamic>> login(@Body() LoginRequest request);

  /// Register new user
  @POST('/auth/register')
  Future<HttpResponse<dynamic>> register(@Body() RegisterRequest request);

  /// Get current user
  @GET('/users/me')
  Future<HttpResponse<dynamic>> getCurrentUser();

  /// Refresh token
  @POST('/auth/refresh')
  Future<HttpResponse<dynamic>> refreshToken(
    @Body() Map<String, dynamic> body,
  );

  /// Logout
  @POST('/auth/logout')
  Future<HttpResponse<void>> logout();
}

/// Manual implementation for when retrofit generator isn't run
class _AuthRemoteDataSource implements AuthRemoteDataSource {
  final Dio _dio;
  final String _baseUrl;

  _AuthRemoteDataSource(this._dio, {String? baseUrl})
      : _baseUrl = baseUrl ?? _dio.options.baseUrl;

  @override
  Future<HttpResponse<dynamic>> login(LoginRequest request) async {
    final response = await _dio.post(
      '$_baseUrl/auth/login',
      data: request.toJson(),
    );
    return HttpResponse(response.data, response);
  }

  @override
  Future<HttpResponse<dynamic>> register(RegisterRequest request) async {
    final response = await _dio.post(
      '$_baseUrl/auth/register',
      data: request.toJson(),
    );
    return HttpResponse(response.data, response);
  }

  @override
  Future<HttpResponse<dynamic>> getCurrentUser() async {
    final response = await _dio.get('$_baseUrl/users/me');
    return HttpResponse(response.data, response);
  }

  @override
  Future<HttpResponse<dynamic>> refreshToken(Map<String, dynamic> body) async {
    final response = await _dio.post(
      '$_baseUrl/auth/refresh',
      data: body,
    );
    return HttpResponse(response.data, response);
  }

  @override
  Future<HttpResponse<void>> logout() async {
    final response = await _dio.post('$_baseUrl/auth/logout');
    return HttpResponse(null, response);
  }
}

