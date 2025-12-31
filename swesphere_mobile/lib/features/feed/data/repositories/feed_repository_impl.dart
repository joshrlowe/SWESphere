import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';

import '../../../../core/error/failures.dart';
import '../../domain/entities/post.dart';
import '../../domain/repositories/feed_repository.dart';
import '../datasources/feed_remote_datasource.dart';
import '../models/post_model.dart';

/// Implementation of FeedRepository
class FeedRepositoryImpl implements FeedRepository {
  final FeedRemoteDataSource remoteDataSource;

  FeedRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, PaginatedPosts>> getHomeFeed({
    int page = 1,
    int size = 20,
  }) async {
    return _handlePaginatedRequest(
      () => remoteDataSource.getHomeFeed(page: page, size: size),
    );
  }

  @override
  Future<Either<Failure, PaginatedPosts>> getExploreFeed({
    int page = 1,
    int size = 20,
  }) async {
    return _handlePaginatedRequest(
      () => remoteDataSource.getExploreFeed(page: page, size: size),
    );
  }

  @override
  Future<Either<Failure, PaginatedPosts>> getUserPosts({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    return _handlePaginatedRequest(
      () => remoteDataSource.getUserPosts(
        username: username,
        page: page,
        size: size,
      ),
    );
  }

  @override
  Future<Either<Failure, Post>> getPost(int postId) async {
    try {
      final post = await remoteDataSource.getPost(postId);
      return Right(post.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, PaginatedPosts>> getPostReplies({
    required int postId,
    int page = 1,
    int size = 20,
  }) async {
    return _handlePaginatedRequest(
      () => remoteDataSource.getPostReplies(
        postId: postId,
        page: page,
        size: size,
      ),
    );
  }

  @override
  Future<Either<Failure, Post>> createPost(CreatePostData data) async {
    try {
      final post = await remoteDataSource.createPost(
        content: data.content,
        replyToId: data.replyToId,
        mediaUrls: data.mediaUrls,
      );
      return Right(post.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> deletePost(int postId) async {
    try {
      await remoteDataSource.deletePost(postId);
      return const Right(null);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, Post>> likePost(int postId) async {
    try {
      await remoteDataSource.likePost(postId);
      // Fetch updated post
      final post = await remoteDataSource.getPost(postId);
      return Right(post.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, Post>> unlikePost(int postId) async {
    try {
      await remoteDataSource.unlikePost(postId);
      // Fetch updated post
      final post = await remoteDataSource.getPost(postId);
      return Right(post.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, Post>> repost(int postId) async {
    try {
      final post = await remoteDataSource.repost(postId);
      return Right(post.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> unrepost(int postId) async {
    try {
      await remoteDataSource.unrepost(postId);
      return const Right(null);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, Post>> bookmarkPost(int postId) async {
    try {
      await remoteDataSource.bookmarkPost(postId);
      final post = await remoteDataSource.getPost(postId);
      return Right(post.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> unbookmarkPost(int postId) async {
    try {
      await remoteDataSource.unbookmarkPost(postId);
      return const Right(null);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, PaginatedPosts>> getBookmarks({
    int page = 1,
    int size = 20,
  }) async {
    return _handlePaginatedRequest(
      () => remoteDataSource.getBookmarks(page: page, size: size),
    );
  }

  @override
  Future<Either<Failure, PaginatedPosts>> searchPosts({
    required String query,
    int page = 1,
    int size = 20,
  }) async {
    return _handlePaginatedRequest(
      () => remoteDataSource.searchPosts(query: query, page: page, size: size),
    );
  }

  Future<Either<Failure, PaginatedPosts>> _handlePaginatedRequest(
    Future<PaginatedPostsResponse> Function() request,
  ) async {
    try {
      final response = await request();
      return Right(PaginatedPosts(
        posts: response.items.map((p) => p.toEntity()).toList(),
        page: response.page,
        totalPages: response.pages,
        total: response.total,
        hasNext: response.hasNext,
        hasPrev: response.hasPrev,
      ));
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  Failure _handleDioError(DioException e) {
    switch (e.response?.statusCode) {
      case 400:
        return const ValidationFailure('Invalid request');
      case 401:
        return const AuthFailure('Not authenticated');
      case 403:
        return const PermissionFailure('Not authorized');
      case 404:
        return const NotFoundFailure('Post not found');
      case 500:
        return const ServerFailure('Server error');
      default:
        if (e.type == DioExceptionType.connectionError) {
          return const NetworkFailure();
        }
        return ServerFailure(e.message ?? 'An error occurred');
    }
  }
}

