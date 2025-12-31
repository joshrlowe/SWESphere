import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/post.dart';
import '../repositories/feed_repository.dart';

/// Create post use case
class CreatePostUseCase {
  final FeedRepository repository;

  CreatePostUseCase(this.repository);

  /// Execute - create a new post
  Future<Either<Failure, Post>> call(CreatePostParams params) async {
    // Validate content
    final validationError = params.validate();
    if (validationError != null) {
      return Left(ValidationFailure(validationError));
    }

    return repository.createPost(CreatePostData(
      content: params.content.trim(),
      replyToId: params.replyToId,
      mediaUrls: params.mediaUrls,
    ));
  }
}

/// Parameters for creating a post
class CreatePostParams {
  final String content;
  final int? replyToId;
  final List<String>? mediaUrls;

  static const int maxContentLength = 280;

  const CreatePostParams({
    required this.content,
    this.replyToId,
    this.mediaUrls,
  });

  /// Validate post content
  String? validate() {
    if (content.trim().isEmpty) {
      return 'Post content cannot be empty';
    }
    if (content.length > maxContentLength) {
      return 'Post must be less than $maxContentLength characters';
    }
    return null;
  }

  /// Characters remaining
  int get remainingCharacters => maxContentLength - content.length;

  /// Is content valid
  bool get isValid => validate() == null;
}

