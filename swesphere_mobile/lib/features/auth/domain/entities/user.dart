import 'package:equatable/equatable.dart';

/// User entity
class User extends Equatable {
  final int id;
  final String username;
  final String email;
  final String? displayName;
  final String? bio;
  final String? avatarUrl;
  final String? bannerUrl;
  final String? location;
  final String? website;
  final int followersCount;
  final int followingCount;
  final int postsCount;
  final bool isVerified;
  final bool isFollowing;
  final DateTime createdAt;

  const User({
    required this.id,
    required this.username,
    required this.email,
    this.displayName,
    this.bio,
    this.avatarUrl,
    this.bannerUrl,
    this.location,
    this.website,
    this.followersCount = 0,
    this.followingCount = 0,
    this.postsCount = 0,
    this.isVerified = false,
    this.isFollowing = false,
    required this.createdAt,
  });

  /// Display name or username
  String get name => displayName ?? username;

  /// User handle with @
  String get handle => '@$username';

  @override
  List<Object?> get props => [
        id,
        username,
        email,
        displayName,
        bio,
        avatarUrl,
        bannerUrl,
        location,
        website,
        followersCount,
        followingCount,
        postsCount,
        isVerified,
        isFollowing,
        createdAt,
      ];

  User copyWith({
    int? id,
    String? username,
    String? email,
    String? displayName,
    String? bio,
    String? avatarUrl,
    String? bannerUrl,
    String? location,
    String? website,
    int? followersCount,
    int? followingCount,
    int? postsCount,
    bool? isVerified,
    bool? isFollowing,
    DateTime? createdAt,
  }) {
    return User(
      id: id ?? this.id,
      username: username ?? this.username,
      email: email ?? this.email,
      displayName: displayName ?? this.displayName,
      bio: bio ?? this.bio,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      bannerUrl: bannerUrl ?? this.bannerUrl,
      location: location ?? this.location,
      website: website ?? this.website,
      followersCount: followersCount ?? this.followersCount,
      followingCount: followingCount ?? this.followingCount,
      postsCount: postsCount ?? this.postsCount,
      isVerified: isVerified ?? this.isVerified,
      isFollowing: isFollowing ?? this.isFollowing,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}

