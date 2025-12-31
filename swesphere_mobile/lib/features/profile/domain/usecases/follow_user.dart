import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../auth/domain/entities/user.dart';
import '../repositories/profile_repository.dart';

/// Follow user use case
class FollowUserUseCase {
  final ProfileRepository repository;

  FollowUserUseCase(this.repository);

  /// Execute - follow a user
  Future<Either<Failure, User>> call(String username) async {
    return repository.followUser(username);
  }
}

/// Unfollow user use case
class UnfollowUserUseCase {
  final ProfileRepository repository;

  UnfollowUserUseCase(this.repository);

  /// Execute - unfollow a user
  Future<Either<Failure, void>> call(String username) async {
    return repository.unfollowUser(username);
  }
}

/// Toggle follow use case
class ToggleFollowUseCase {
  final ProfileRepository repository;

  ToggleFollowUseCase(this.repository);

  /// Execute - toggle follow state
  Future<Either<Failure, User?>> call({
    required String username,
    required bool isCurrentlyFollowing,
  }) async {
    if (isCurrentlyFollowing) {
      final result = await repository.unfollowUser(username);
      return result.map((_) => null);
    } else {
      return repository.followUser(username);
    }
  }
}

