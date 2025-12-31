import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/post.dart';
import '../repositories/feed_repository.dart';

/// Like post use case
class LikePostUseCase {
  final FeedRepository repository;

  LikePostUseCase(this.repository);

  /// Execute - like a post
  Future<Either<Failure, Post>> call(int postId) async {
    return repository.likePost(postId);
  }
}

/// Unlike post use case
class UnlikePostUseCase {
  final FeedRepository repository;

  UnlikePostUseCase(this.repository);

  /// Execute - unlike a post
  Future<Either<Failure, Post>> call(int postId) async {
    return repository.unlikePost(postId);
  }
}

/// Toggle like use case - handles both like and unlike
class ToggleLikeUseCase {
  final FeedRepository repository;

  ToggleLikeUseCase(this.repository);

  /// Execute - toggle like state
  Future<Either<Failure, Post>> call({
    required int postId,
    required bool isCurrentlyLiked,
  }) async {
    if (isCurrentlyLiked) {
      return repository.unlikePost(postId);
    } else {
      return repository.likePost(postId);
    }
  }
}

