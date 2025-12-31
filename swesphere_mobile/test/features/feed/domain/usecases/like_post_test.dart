import 'package:dartz/dartz.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/core/error/failures.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/feed/domain/entities/post.dart';
import 'package:swesphere_mobile/features/feed/domain/repositories/feed_repository.dart';
import 'package:swesphere_mobile/features/feed/domain/usecases/like_post.dart';

// Mock repository
class MockFeedRepository implements FeedRepository {
  Post? postToReturn;
  Failure? failureToReturn;
  bool likeWasCalled = false;
  bool unlikeWasCalled = false;

  @override
  Future<Either<Failure, Post>> likePost(int postId) async {
    likeWasCalled = true;
    if (postToReturn != null) {
      return Right(postToReturn!);
    }
    return Left(failureToReturn ?? const ServerFailure('Error'));
  }

  @override
  Future<Either<Failure, Post>> unlikePost(int postId) async {
    unlikeWasCalled = true;
    if (postToReturn != null) {
      return Right(postToReturn!);
    }
    return Left(failureToReturn ?? const ServerFailure('Error'));
  }

  // Other methods not needed for this test
  @override
  Future<Either<Failure, PaginatedPosts>> getHomeFeed({int page = 1, int size = 20}) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedPosts>> getExploreFeed({int page = 1, int size = 20}) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedPosts>> getUserPosts({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, Post>> getPost(int postId) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedPosts>> getPostReplies({
    required int postId,
    int page = 1,
    int size = 20,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, Post>> createPost(CreatePostData data) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, void>> deletePost(int postId) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, Post>> repost(int postId) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, void>> unrepost(int postId) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, Post>> bookmarkPost(int postId) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, void>> unbookmarkPost(int postId) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedPosts>> getBookmarks({int page = 1, int size = 20}) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, PaginatedPosts>> searchPosts({
    required String query,
    int page = 1,
    int size = 20,
  }) async {
    throw UnimplementedError();
  }
}

void main() {
  late MockFeedRepository repository;

  final testUser = User(
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    createdAt: DateTime(2024, 1, 1),
  );

  final testPost = Post(
    id: 1,
    content: 'Test post',
    author: testUser,
    likesCount: 5,
    isLiked: false,
    createdAt: DateTime(2024, 1, 1),
  );

  final likedPost = Post(
    id: 1,
    content: 'Test post',
    author: testUser,
    likesCount: 6,
    isLiked: true,
    createdAt: DateTime(2024, 1, 1),
  );

  setUp(() {
    repository = MockFeedRepository();
  });

  group('LikePostUseCase', () {
    test('calls likePost on repository', () async {
      final useCase = LikePostUseCase(repository);
      repository.postToReturn = likedPost;

      await useCase(1);

      expect(repository.likeWasCalled, true);
    });

    test('returns liked post on success', () async {
      final useCase = LikePostUseCase(repository);
      repository.postToReturn = likedPost;

      final result = await useCase(1);

      expect(result.isRight(), true);
      result.fold(
        (failure) => fail('Expected success'),
        (post) {
          expect(post.isLiked, true);
          expect(post.likesCount, 6);
        },
      );
    });
  });

  group('UnlikePostUseCase', () {
    test('calls unlikePost on repository', () async {
      final useCase = UnlikePostUseCase(repository);
      repository.postToReturn = testPost;

      await useCase(1);

      expect(repository.unlikeWasCalled, true);
    });

    test('returns unliked post on success', () async {
      final useCase = UnlikePostUseCase(repository);
      repository.postToReturn = testPost;

      final result = await useCase(1);

      expect(result.isRight(), true);
      result.fold(
        (failure) => fail('Expected success'),
        (post) {
          expect(post.isLiked, false);
          expect(post.likesCount, 5);
        },
      );
    });
  });

  group('ToggleLikeUseCase', () {
    test('calls unlikePost when currently liked', () async {
      final useCase = ToggleLikeUseCase(repository);
      repository.postToReturn = testPost;

      await useCase(postId: 1, isCurrentlyLiked: true);

      expect(repository.unlikeWasCalled, true);
      expect(repository.likeWasCalled, false);
    });

    test('calls likePost when not currently liked', () async {
      final useCase = ToggleLikeUseCase(repository);
      repository.postToReturn = likedPost;

      await useCase(postId: 1, isCurrentlyLiked: false);

      expect(repository.likeWasCalled, true);
      expect(repository.unlikeWasCalled, false);
    });
  });
}

