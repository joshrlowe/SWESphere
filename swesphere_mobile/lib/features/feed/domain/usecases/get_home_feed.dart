import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../repositories/feed_repository.dart';

/// Get home feed use case
class GetHomeFeedUseCase {
  final FeedRepository repository;

  GetHomeFeedUseCase(this.repository);

  /// Execute - get home feed with pagination
  Future<Either<Failure, PaginatedPosts>> call(GetHomeFeedParams params) async {
    return repository.getHomeFeed(
      page: params.page,
      size: params.size,
    );
  }
}

/// Parameters for getting home feed
class GetHomeFeedParams {
  final int page;
  final int size;

  const GetHomeFeedParams({
    this.page = 1,
    this.size = 20,
  });
}

