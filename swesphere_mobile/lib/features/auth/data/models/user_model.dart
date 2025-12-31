import 'package:json_annotation/json_annotation.dart';
import '../../domain/entities/user.dart';

part 'user_model.g.dart';

/// User model for JSON serialization
@JsonSerializable()
class UserModel {
  final int id;
  final String username;
  final String email;
  @JsonKey(name: 'display_name')
  final String? displayName;
  final String? bio;
  @JsonKey(name: 'avatar_url')
  final String? avatarUrl;
  @JsonKey(name: 'banner_url')
  final String? bannerUrl;
  final String? location;
  final String? website;
  @JsonKey(name: 'followers_count')
  final int followersCount;
  @JsonKey(name: 'following_count')
  final int followingCount;
  @JsonKey(name: 'posts_count')
  final int postsCount;
  @JsonKey(name: 'is_verified')
  final bool isVerified;
  @JsonKey(name: 'is_following')
  final bool isFollowing;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  const UserModel({
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

  factory UserModel.fromJson(Map<String, dynamic> json) =>
      _$UserModelFromJson(json);

  Map<String, dynamic> toJson() => _$UserModelToJson(this);

  /// Convert to domain entity
  User toEntity() {
    return User(
      id: id,
      username: username,
      email: email,
      displayName: displayName,
      bio: bio,
      avatarUrl: avatarUrl,
      bannerUrl: bannerUrl,
      location: location,
      website: website,
      followersCount: followersCount,
      followingCount: followingCount,
      postsCount: postsCount,
      isVerified: isVerified,
      isFollowing: isFollowing,
      createdAt: createdAt,
    );
  }

  /// Create from domain entity
  factory UserModel.fromEntity(User user) {
    return UserModel(
      id: user.id,
      username: user.username,
      email: user.email,
      displayName: user.displayName,
      bio: user.bio,
      avatarUrl: user.avatarUrl,
      bannerUrl: user.bannerUrl,
      location: user.location,
      website: user.website,
      followersCount: user.followersCount,
      followingCount: user.followingCount,
      postsCount: user.postsCount,
      isVerified: user.isVerified,
      isFollowing: user.isFollowing,
      createdAt: user.createdAt,
    );
  }
}

