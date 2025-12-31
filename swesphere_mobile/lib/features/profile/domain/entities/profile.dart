import 'package:equatable/equatable.dart';

import '../../../auth/domain/entities/user.dart';

/// Profile entity - extends user with additional profile info
class Profile extends Equatable {
  final User user;
  final bool isOwnProfile;
  final bool isBlocked;
  final bool isMuted;

  const Profile({
    required this.user,
    this.isOwnProfile = false,
    this.isBlocked = false,
    this.isMuted = false,
  });

  @override
  List<Object?> get props => [user, isOwnProfile, isBlocked, isMuted];

  Profile copyWith({
    User? user,
    bool? isOwnProfile,
    bool? isBlocked,
    bool? isMuted,
  }) {
    return Profile(
      user: user ?? this.user,
      isOwnProfile: isOwnProfile ?? this.isOwnProfile,
      isBlocked: isBlocked ?? this.isBlocked,
      isMuted: isMuted ?? this.isMuted,
    );
  }
}

/// Profile stats
class ProfileStats extends Equatable {
  final int postsCount;
  final int followersCount;
  final int followingCount;
  final int likesCount;

  const ProfileStats({
    this.postsCount = 0,
    this.followersCount = 0,
    this.followingCount = 0,
    this.likesCount = 0,
  });

  @override
  List<Object?> get props => [
        postsCount,
        followersCount,
        followingCount,
        likesCount,
      ];
}

