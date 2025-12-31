import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';

import '../../../../core/error/failures.dart';
import '../../../auth/domain/entities/user.dart';
import '../../../feed/domain/entities/post.dart';
import '../../domain/repositories/profile_repository.dart';
import '../datasources/profile_remote_datasource.dart';
import '../models/profile_model.dart';

/// Implementation of ProfileRepository
class ProfileRepositoryImpl implements ProfileRepository {
  final ProfileRemoteDataSource remoteDataSource;

  ProfileRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, User>> getProfile(String username) async {
    try {
      final userModel = await remoteDataSource.getProfile(username);
      return Right(userModel.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, User>> updateProfile(UpdateProfileData data) async {
    try {
      final request = UpdateProfileRequest(
        displayName: data.displayName,
        bio: data.bio,
        location: data.location,
        website: data.website,
        avatarUrl: data.avatarUrl,
        bannerUrl: data.bannerUrl,
      );
      final userModel = await remoteDataSource.updateProfile(request);
      return Right(userModel.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, User>> followUser(String username) async {
    try {
      final userModel = await remoteDataSource.followUser(username);
      return Right(userModel.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> unfollowUser(String username) async {
    try {
      await remoteDataSource.unfollowUser(username);
      return const Right(null);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, PaginatedUsers>> getFollowers({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    try {
      final response = await remoteDataSource.getFollowers(
        username: username,
        page: page,
        size: size,
      );
      return Right(PaginatedUsers(
        users: response.items.map((u) => u.toEntity()).toList(),
        page: response.page,
        totalPages: response.pages,
        hasNext: response.hasNext,
      ));
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, PaginatedUsers>> getFollowing({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    try {
      final response = await remoteDataSource.getFollowing(
        username: username,
        page: page,
        size: size,
      );
      return Right(PaginatedUsers(
        users: response.items.map((u) => u.toEntity()).toList(),
        page: response.page,
        totalPages: response.pages,
        hasNext: response.hasNext,
      ));
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, PaginatedProfilePosts>> getUserPosts({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    return _handlePostsRequest(() => remoteDataSource.getUserPosts(
      username: username,
      page: page,
      size: size,
    ));
  }

  @override
  Future<Either<Failure, PaginatedProfilePosts>> getUserReplies({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    return _handlePostsRequest(() => remoteDataSource.getUserReplies(
      username: username,
      page: page,
      size: size,
    ));
  }

  @override
  Future<Either<Failure, PaginatedProfilePosts>> getUserMedia({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    return _handlePostsRequest(() => remoteDataSource.getUserMedia(
      username: username,
      page: page,
      size: size,
    ));
  }

  @override
  Future<Either<Failure, PaginatedProfilePosts>> getUserLikes({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    return _handlePostsRequest(() => remoteDataSource.getUserLikes(
      username: username,
      page: page,
      size: size,
    ));
  }

  @override
  Future<Either<Failure, void>> blockUser(String username) async {
    try {
      await remoteDataSource.blockUser(username);
      return const Right(null);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> unblockUser(String username) async {
    try {
      await remoteDataSource.unblockUser(username);
      return const Right(null);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> muteUser(String username) async {
    try {
      await remoteDataSource.muteUser(username);
      return const Right(null);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> unmuteUser(String username) async {
    try {
      await remoteDataSource.unmuteUser(username);
      return const Right(null);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, String>> uploadAvatar(String filePath) async {
    try {
      final url = await remoteDataSource.uploadAvatar(filePath);
      return Right(url);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, String>> uploadBanner(String filePath) async {
    try {
      final url = await remoteDataSource.uploadBanner(filePath);
      return Right(url);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  Future<Either<Failure, PaginatedProfilePosts>> _handlePostsRequest(
    Future<dynamic> Function() request,
  ) async {
    try {
      final response = await request();
      return Right(PaginatedProfilePosts(
        posts: response.items
            .map<Post>((p) => p.toEntity())
            .toList(),
        page: response.page,
        hasNext: response.hasNext,
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
        return const AuthFailure();
      case 403:
        return const PermissionFailure();
      case 404:
        return const NotFoundFailure('User not found');
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

