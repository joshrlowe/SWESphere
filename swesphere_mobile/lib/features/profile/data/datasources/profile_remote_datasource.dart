import 'package:dio/dio.dart';

import '../../../auth/data/models/user_model.dart';
import '../../../feed/data/models/post_model.dart';
import '../models/profile_model.dart';

/// Remote data source for profile operations
class ProfileRemoteDataSource {
  final Dio _dio;

  ProfileRemoteDataSource(this._dio);

  /// Get user profile by username
  Future<UserModel> getProfile(String username) async {
    final response = await _dio.get('/users/$username');
    return UserModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Update profile
  Future<UserModel> updateProfile(UpdateProfileRequest request) async {
    final response = await _dio.patch(
      '/users/me',
      data: request.toJson(),
    );
    return UserModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Follow user
  Future<UserModel> followUser(String username) async {
    final response = await _dio.post('/users/$username/follow');
    return UserModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Unfollow user
  Future<void> unfollowUser(String username) async {
    await _dio.delete('/users/$username/follow');
  }

  /// Get followers
  Future<PaginatedUsersResponse> getFollowers({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/users/$username/followers',
      queryParameters: {'page': page, 'size': size},
    );
    return PaginatedUsersResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Get following
  Future<PaginatedUsersResponse> getFollowing({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/users/$username/following',
      queryParameters: {'page': page, 'size': size},
    );
    return PaginatedUsersResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Get user posts
  Future<PaginatedPostsResponse> getUserPosts({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/users/$username/posts',
      queryParameters: {'page': page, 'size': size},
    );
    return PaginatedPostsResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Get user replies
  Future<PaginatedPostsResponse> getUserReplies({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/users/$username/replies',
      queryParameters: {'page': page, 'size': size},
    );
    return PaginatedPostsResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Get user media
  Future<PaginatedPostsResponse> getUserMedia({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/users/$username/media',
      queryParameters: {'page': page, 'size': size},
    );
    return PaginatedPostsResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Get user likes
  Future<PaginatedPostsResponse> getUserLikes({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/users/$username/likes',
      queryParameters: {'page': page, 'size': size},
    );
    return PaginatedPostsResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Block user
  Future<void> blockUser(String username) async {
    await _dio.post('/users/$username/block');
  }

  /// Unblock user
  Future<void> unblockUser(String username) async {
    await _dio.delete('/users/$username/block');
  }

  /// Mute user
  Future<void> muteUser(String username) async {
    await _dio.post('/users/$username/mute');
  }

  /// Unmute user
  Future<void> unmuteUser(String username) async {
    await _dio.delete('/users/$username/mute');
  }

  /// Upload avatar
  Future<String> uploadAvatar(String filePath) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath, filename: 'avatar.jpg'),
    });
    final response = await _dio.post('/users/me/avatar', data: formData);
    return response.data['avatar_url'] as String;
  }

  /// Upload banner
  Future<String> uploadBanner(String filePath) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath, filename: 'banner.jpg'),
    });
    final response = await _dio.post('/users/me/banner', data: formData);
    return response.data['banner_url'] as String;
  }
}

