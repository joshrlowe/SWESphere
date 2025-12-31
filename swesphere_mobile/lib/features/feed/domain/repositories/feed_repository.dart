import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/post.dart';

/// Paginated response wrapper
class PaginatedPosts {
  final List<Post> posts;
  final int page;
  final int totalPages;
  final int total;
  final bool hasNext;
  final bool hasPrev;

  const PaginatedPosts({
    required this.posts,
    required this.page,
    required this.totalPages,
    required this.total,
    required this.hasNext,
    required this.hasPrev,
  });
}

/// Create post data
class CreatePostData {
  final String content;
  final int? replyToId;
  final List<String>? mediaUrls;

  const CreatePostData({
    required this.content,
    this.replyToId,
    this.mediaUrls,
  });
}

/// Abstract feed repository
abstract class FeedRepository {
  /// Get home feed (posts from followed users)
  Future<Either<Failure, PaginatedPosts>> getHomeFeed({
    int page = 1,
    int size = 20,
  });

  /// Get explore feed (all posts)
  Future<Either<Failure, PaginatedPosts>> getExploreFeed({
    int page = 1,
    int size = 20,
  });

  /// Get posts by user
  Future<Either<Failure, PaginatedPosts>> getUserPosts({
    required String username,
    int page = 1,
    int size = 20,
  });

  /// Get single post by ID
  Future<Either<Failure, Post>> getPost(int postId);

  /// Get post replies
  Future<Either<Failure, PaginatedPosts>> getPostReplies({
    required int postId,
    int page = 1,
    int size = 20,
  });

  /// Create a new post
  Future<Either<Failure, Post>> createPost(CreatePostData data);

  /// Delete a post
  Future<Either<Failure, void>> deletePost(int postId);

  /// Like a post
  Future<Either<Failure, Post>> likePost(int postId);

  /// Unlike a post
  Future<Either<Failure, Post>> unlikePost(int postId);

  /// Repost a post
  Future<Either<Failure, Post>> repost(int postId);

  /// Remove repost
  Future<Either<Failure, void>> unrepost(int postId);

  /// Bookmark a post
  Future<Either<Failure, Post>> bookmarkPost(int postId);

  /// Remove bookmark
  Future<Either<Failure, void>> unbookmarkPost(int postId);

  /// Get bookmarked posts
  Future<Either<Failure, PaginatedPosts>> getBookmarks({
    int page = 1,
    int size = 20,
  });

  /// Search posts
  Future<Either<Failure, PaginatedPosts>> searchPosts({
    required String query,
    int page = 1,
    int size = 20,
  });
}

