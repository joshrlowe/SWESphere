import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../auth/domain/entities/user.dart';
import '../../../feed/domain/entities/post.dart';

/// Update profile data
class UpdateProfileData {
  final String? displayName;
  final String? bio;
  final String? location;
  final String? website;
  final String? avatarUrl;
  final String? bannerUrl;

  const UpdateProfileData({
    this.displayName,
    this.bio,
    this.location,
    this.website,
    this.avatarUrl,
    this.bannerUrl,
  });
}

/// Paginated users response
class PaginatedUsers {
  final List<User> users;
  final int page;
  final int totalPages;
  final bool hasNext;

  const PaginatedUsers({
    required this.users,
    required this.page,
    required this.totalPages,
    required this.hasNext,
  });
}

/// Paginated posts response for profile
class PaginatedProfilePosts {
  final List<Post> posts;
  final int page;
  final bool hasNext;

  const PaginatedProfilePosts({
    required this.posts,
    required this.page,
    required this.hasNext,
  });
}

/// Abstract profile repository
abstract class ProfileRepository {
  /// Get user profile by username
  Future<Either<Failure, User>> getProfile(String username);

  /// Update current user's profile
  Future<Either<Failure, User>> updateProfile(UpdateProfileData data);

  /// Follow a user
  Future<Either<Failure, User>> followUser(String username);

  /// Unfollow a user
  Future<Either<Failure, void>> unfollowUser(String username);

  /// Get followers of a user
  Future<Either<Failure, PaginatedUsers>> getFollowers({
    required String username,
    int page = 1,
    int size = 20,
  });

  /// Get users that a user is following
  Future<Either<Failure, PaginatedUsers>> getFollowing({
    required String username,
    int page = 1,
    int size = 20,
  });

  /// Get user's posts
  Future<Either<Failure, PaginatedProfilePosts>> getUserPosts({
    required String username,
    int page = 1,
    int size = 20,
  });

  /// Get user's replies
  Future<Either<Failure, PaginatedProfilePosts>> getUserReplies({
    required String username,
    int page = 1,
    int size = 20,
  });

  /// Get user's media posts
  Future<Either<Failure, PaginatedProfilePosts>> getUserMedia({
    required String username,
    int page = 1,
    int size = 20,
  });

  /// Get user's liked posts
  Future<Either<Failure, PaginatedProfilePosts>> getUserLikes({
    required String username,
    int page = 1,
    int size = 20,
  });

  /// Block a user
  Future<Either<Failure, void>> blockUser(String username);

  /// Unblock a user
  Future<Either<Failure, void>> unblockUser(String username);

  /// Mute a user
  Future<Either<Failure, void>> muteUser(String username);

  /// Unmute a user
  Future<Either<Failure, void>> unmuteUser(String username);

  /// Upload avatar image
  Future<Either<Failure, String>> uploadAvatar(String filePath);

  /// Upload banner image
  Future<Either<Failure, String>> uploadBanner(String filePath);
}

