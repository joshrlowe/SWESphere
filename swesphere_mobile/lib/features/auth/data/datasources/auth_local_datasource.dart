import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hive_flutter/hive_flutter.dart';

import '../models/user_model.dart';

/// Storage keys
abstract class AuthStorageKeys {
  static const String accessToken = 'access_token';
  static const String refreshToken = 'refresh_token';
  static const String cachedUser = 'cached_user';
  static const String userBox = 'user_box';
}

/// Local data source for authentication (token storage and caching)
abstract class AuthLocalDataSource {
  /// Save access token
  Future<void> saveAccessToken(String token);

  /// Get access token
  Future<String?> getAccessToken();

  /// Save refresh token
  Future<void> saveRefreshToken(String token);

  /// Get refresh token
  Future<String?> getRefreshToken();

  /// Clear all tokens
  Future<void> clearTokens();

  /// Cache user
  Future<void> cacheUser(UserModel user);

  /// Get cached user
  Future<UserModel?> getCachedUser();

  /// Clear cached user
  Future<void> clearCachedUser();

  /// Check if tokens exist
  Future<bool> hasTokens();
}

/// Implementation using Flutter Secure Storage and Hive
class AuthLocalDataSourceImpl implements AuthLocalDataSource {
  final FlutterSecureStorage _secureStorage;
  final Box<String>? _userBox;

  AuthLocalDataSourceImpl({
    required FlutterSecureStorage secureStorage,
    Box<String>? userBox,
  })  : _secureStorage = secureStorage,
        _userBox = userBox;

  @override
  Future<void> saveAccessToken(String token) async {
    await _secureStorage.write(
      key: AuthStorageKeys.accessToken,
      value: token,
    );
  }

  @override
  Future<String?> getAccessToken() async {
    return _secureStorage.read(key: AuthStorageKeys.accessToken);
  }

  @override
  Future<void> saveRefreshToken(String token) async {
    await _secureStorage.write(
      key: AuthStorageKeys.refreshToken,
      value: token,
    );
  }

  @override
  Future<String?> getRefreshToken() async {
    return _secureStorage.read(key: AuthStorageKeys.refreshToken);
  }

  @override
  Future<void> clearTokens() async {
    await _secureStorage.delete(key: AuthStorageKeys.accessToken);
    await _secureStorage.delete(key: AuthStorageKeys.refreshToken);
  }

  @override
  Future<void> cacheUser(UserModel user) async {
    final userJson = jsonEncode(user.toJson());
    if (_userBox != null) {
      await _userBox.put(AuthStorageKeys.cachedUser, userJson);
    } else {
      await _secureStorage.write(
        key: AuthStorageKeys.cachedUser,
        value: userJson,
      );
    }
  }

  @override
  Future<UserModel?> getCachedUser() async {
    String? userJson;
    
    if (_userBox != null) {
      userJson = _userBox.get(AuthStorageKeys.cachedUser);
    } else {
      userJson = await _secureStorage.read(key: AuthStorageKeys.cachedUser);
    }

    if (userJson == null) return null;

    try {
      final Map<String, dynamic> json = jsonDecode(userJson);
      return UserModel.fromJson(json);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> clearCachedUser() async {
    if (_userBox != null) {
      await _userBox.delete(AuthStorageKeys.cachedUser);
    } else {
      await _secureStorage.delete(key: AuthStorageKeys.cachedUser);
    }
  }

  @override
  Future<bool> hasTokens() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }
}

