import 'package:dio/dio.dart';

import '../models/post_model.dart';

/// Remote data source for feed/posts
class FeedRemoteDataSource {
  final Dio _dio;

  FeedRemoteDataSource(this._dio);

  /// Get home feed
  Future<PaginatedPostsResponse> getHomeFeed({
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/posts/feed',
      queryParameters: {'page': page, 'size': size},
    );
    return PaginatedPostsResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Get explore feed
  Future<PaginatedPostsResponse> getExploreFeed({
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/posts',
      queryParameters: {'page': page, 'size': size},
    );
    return PaginatedPostsResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Get posts by username
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

  /// Get single post
  Future<PostModel> getPost(int postId) async {
    final response = await _dio.get('/posts/$postId');
    return PostModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Get post replies
  Future<PaginatedPostsResponse> getPostReplies({
    required int postId,
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/posts/$postId/replies',
      queryParameters: {'page': page, 'size': size},
    );
    return PaginatedPostsResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Create post
  Future<PostModel> createPost({
    required String content,
    int? replyToId,
    List<String>? mediaUrls,
  }) async {
    final response = await _dio.post(
      '/posts',
      data: {
        'content': content,
        if (replyToId != null) 'reply_to_id': replyToId,
        if (mediaUrls != null) 'media_urls': mediaUrls,
      },
    );
    return PostModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Delete post
  Future<void> deletePost(int postId) async {
    await _dio.delete('/posts/$postId');
  }

  /// Like post
  Future<void> likePost(int postId) async {
    await _dio.post('/posts/$postId/like');
  }

  /// Unlike post
  Future<void> unlikePost(int postId) async {
    await _dio.delete('/posts/$postId/like');
  }

  /// Repost
  Future<PostModel> repost(int postId) async {
    final response = await _dio.post('/posts/$postId/repost');
    return PostModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Remove repost
  Future<void> unrepost(int postId) async {
    await _dio.delete('/posts/$postId/repost');
  }

  /// Bookmark post
  Future<void> bookmarkPost(int postId) async {
    await _dio.post('/posts/$postId/bookmark');
  }

  /// Remove bookmark
  Future<void> unbookmarkPost(int postId) async {
    await _dio.delete('/posts/$postId/bookmark');
  }

  /// Get bookmarks
  Future<PaginatedPostsResponse> getBookmarks({
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/bookmarks',
      queryParameters: {'page': page, 'size': size},
    );
    return PaginatedPostsResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Search posts
  Future<PaginatedPostsResponse> searchPosts({
    required String query,
    int page = 1,
    int size = 20,
  }) async {
    final response = await _dio.get(
      '/search/posts',
      queryParameters: {'q': query, 'page': page, 'size': size},
    );
    return PaginatedPostsResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }
}

