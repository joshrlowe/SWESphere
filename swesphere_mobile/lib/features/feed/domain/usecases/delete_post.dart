import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../repositories/feed_repository.dart';

/// Delete post use case
class DeletePostUseCase {
  final FeedRepository repository;

  DeletePostUseCase(this.repository);

  /// Execute - delete a post
  Future<Either<Failure, void>> call(int postId) async {
    return repository.deletePost(postId);
  }
}

