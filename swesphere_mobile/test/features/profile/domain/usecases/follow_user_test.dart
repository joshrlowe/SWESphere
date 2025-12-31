import 'package:dartz/dartz.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/core/error/failures.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/feed/domain/entities/post.dart';
import 'package:swesphere_mobile/features/profile/domain/repositories/profile_repository.dart';
import 'package:swesphere_mobile/features/profile/domain/usecases/follow_user.dart';

// Mock repository
class MockProfileRepository implements ProfileRepository {
  User? userToReturn;
  Failure? failureToReturn;
  bool followWasCalled = false;
  bool unfollowWasCalled = false;

  @override
  Future<Either<Failure, User>> followUser(String username) async {
    followWasCalled = true;
    if (userToReturn != null) {
      return Right(userToReturn!);
    }
    return Left(failureToReturn ?? const ServerFailure('Error'));
  }

  @override
  Future<Either<Failure, void>> unfollowUser(String username) async {
    unfollowWasCalled = true;
    if (failureToReturn != null) {
      return Left(failureToReturn!);
    }
    return const Right(null);
  }

  // Other methods not needed for this test
  @override
  Future<Either<Failure, User>> getProfile(String username) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, User>> updateProfile(UpdateProfileData data) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedUsers>> getFollowers({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedUsers>> getFollowing({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedProfilePosts>> getUserPosts({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedProfilePosts>> getUserReplies({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedProfilePosts>> getUserMedia({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedProfilePosts>> getUserLikes({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, void>> blockUser(String username) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, void>> unblockUser(String username) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, void>> muteUser(String username) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, void>> unmuteUser(String username) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, String>> uploadAvatar(String filePath) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, String>> uploadBanner(String filePath) async {
    throw UnimplementedError();
  }
}

void main() {
  late MockProfileRepository repository;

  final testUser = User(
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    isFollowing: true,
    followersCount: 101,
    createdAt: DateTime(2024, 1, 1),
  );

  setUp(() {
    repository = MockProfileRepository();
  });

  group('FollowUserUseCase', () {
    test('calls followUser on repository', () async {
      final useCase = FollowUserUseCase(repository);
      repository.userToReturn = testUser;

      await useCase('testuser');

      expect(repository.followWasCalled, true);
    });

    test('returns user on success', () async {
      final useCase = FollowUserUseCase(repository);
      repository.userToReturn = testUser;

      final result = await useCase('testuser');

      expect(result.isRight(), true);
      result.fold(
        (failure) => fail('Expected success'),
        (user) {
          expect(user.isFollowing, true);
          expect(user.followersCount, 101);
        },
      );
    });

    test('returns failure on error', () async {
      final useCase = FollowUserUseCase(repository);
      repository.failureToReturn = const ServerFailure('Failed to follow');

      final result = await useCase('testuser');

      expect(result.isLeft(), true);
    });
  });

  group('UnfollowUserUseCase', () {
    test('calls unfollowUser on repository', () async {
      final useCase = UnfollowUserUseCase(repository);

      await useCase('testuser');

      expect(repository.unfollowWasCalled, true);
    });

    test('returns success on unfollow', () async {
      final useCase = UnfollowUserUseCase(repository);

      final result = await useCase('testuser');

      expect(result.isRight(), true);
    });
  });

  group('ToggleFollowUseCase', () {
    test('calls unfollowUser when currently following', () async {
      final useCase = ToggleFollowUseCase(repository);

      await useCase(username: 'testuser', isCurrentlyFollowing: true);

      expect(repository.unfollowWasCalled, true);
      expect(repository.followWasCalled, false);
    });

    test('calls followUser when not currently following', () async {
      final useCase = ToggleFollowUseCase(repository);
      repository.userToReturn = testUser;

      await useCase(username: 'testuser', isCurrentlyFollowing: false);

      expect(repository.followWasCalled, true);
      expect(repository.unfollowWasCalled, false);
    });

    test('returns null user on unfollow success', () async {
      final useCase = ToggleFollowUseCase(repository);

      final result = await useCase(username: 'testuser', isCurrentlyFollowing: true);

      expect(result.isRight(), true);
      result.fold(
        (failure) => fail('Expected success'),
        (user) => expect(user, isNull),
      );
    });

    test('returns user on follow success', () async {
      final useCase = ToggleFollowUseCase(repository);
      repository.userToReturn = testUser;

      final result = await useCase(username: 'testuser', isCurrentlyFollowing: false);

      expect(result.isRight(), true);
      result.fold(
        (failure) => fail('Expected success'),
        (user) => expect(user, isNotNull),
      );
    });
  });
}

