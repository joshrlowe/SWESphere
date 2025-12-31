import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/profile/domain/entities/profile.dart';
import 'package:swesphere_mobile/features/profile/domain/usecases/update_profile.dart';
import 'package:swesphere_mobile/features/profile/data/models/profile_model.dart';

void main() {
  group('Profile Flow Integration', () {
    test('Profile entity creation and manipulation', () {
      final user = User(
        id: 1,
        username: 'profileuser',
        email: 'profile@example.com',
        displayName: 'Profile User',
        bio: 'Software Developer | Open Source Enthusiast',
        location: 'New York, NY',
        website: 'https://profileuser.dev',
        followersCount: 5000,
        followingCount: 200,
        postsCount: 150,
        isVerified: true,
        isFollowing: false,
        createdAt: DateTime.utc(2023, 6, 1),
      );

      final profile = Profile(
        user: user,
        isOwnProfile: true,
        isBlocked: false,
        isMuted: false,
      );

      expect(profile.user.username, 'profileuser');
      expect(profile.isOwnProfile, true);

      // Simulate viewing someone else's profile
      final otherProfile = profile.copyWith(
        isOwnProfile: false,
        user: user.copyWith(isFollowing: true),
      );

      expect(otherProfile.isOwnProfile, false);
      expect(otherProfile.user.isFollowing, true);
    });

    test('UpdateProfileParams validation workflow', () {
      // Valid update
      const validUpdate = UpdateProfileParams(
        displayName: 'John Doe',
        bio: 'Building awesome software 🚀',
        location: 'San Francisco',
        website: 'https://johndoe.dev',
      );
      expect(validUpdate.validate(), isNull);

      // Test display name limit
      final longDisplayName = UpdateProfileParams(
        displayName: 'a' * 51,
      );
      expect(longDisplayName.validate(), contains('Display name'));

      // Test bio limit
      final longBio = UpdateProfileParams(
        bio: 'a' * 161,
      );
      expect(longBio.validate(), contains('Bio'));

      // Test location limit
      final longLocation = UpdateProfileParams(
        location: 'a' * 31,
      );
      expect(longLocation.validate(), contains('Location'));

      // Test invalid website
      const invalidWebsite = UpdateProfileParams(
        website: 'not-a-valid-url',
      );
      expect(invalidWebsite.validate(), contains('valid website'));

      // Valid URLs
      const validUrls = [
        'https://example.com',
        'http://test.org',
        'www.site.co',
        'mysite.io',
      ];

      for (final url in validUrls) {
        final params = UpdateProfileParams(website: url);
        expect(params.validate(), isNull, reason: 'URL should be valid: $url');
      }
    });

    test('UpdateProfileRequest JSON serialization', () {
      const request = UpdateProfileRequest(
        displayName: 'Updated Name',
        bio: 'New bio',
        location: 'Updated Location',
        website: 'https://updated.com',
      );

      final json = request.toJson();

      // Null values should be removed
      expect(json.containsKey('avatar_url'), false);
      expect(json.containsKey('banner_url'), false);

      // Non-null values should be present
      expect(json['display_name'], 'Updated Name');
      expect(json['bio'], 'New bio');
      expect(json['location'], 'Updated Location');
      expect(json['website'], 'https://updated.com');
    });

    test('PaginatedUsersResponse parsing', () {
      final usersJson = {
        'items': [
          {
            'id': 1,
            'username': 'follower1',
            'email': 'follower1@test.com',
            'display_name': 'Follower One',
            'followers_count': 100,
            'following_count': 50,
            'created_at': '2024-01-01T00:00:00.000Z',
          },
          {
            'id': 2,
            'username': 'follower2',
            'email': 'follower2@test.com',
            'display_name': 'Follower Two',
            'followers_count': 200,
            'following_count': 100,
            'created_at': '2024-02-01T00:00:00.000Z',
          },
        ],
        'page': 1,
        'pages': 3,
        'total': 50,
        'has_next': true,
        'has_prev': false,
      };

      final response = PaginatedUsersResponse.fromJson(usersJson);

      expect(response.items.length, 2);
      expect(response.items[0].username, 'follower1');
      expect(response.items[1].username, 'follower2');
      expect(response.page, 1);
      expect(response.pages, 3);
      expect(response.total, 50);
      expect(response.hasNext, true);
    });

    test('ProfileStats equality', () {
      const stats1 = ProfileStats(
        postsCount: 100,
        followersCount: 1000,
        followingCount: 500,
        likesCount: 2000,
      );

      const stats2 = ProfileStats(
        postsCount: 100,
        followersCount: 1000,
        followingCount: 500,
        likesCount: 2000,
      );

      const stats3 = ProfileStats(
        postsCount: 100,
        followersCount: 999, // Different
        followingCount: 500,
        likesCount: 2000,
      );

      expect(stats1, equals(stats2));
      expect(stats1, isNot(equals(stats3)));
    });

    test('User follow state transitions', () {
      final user = User(
        id: 1,
        username: 'targetuser',
        email: 'target@test.com',
        followersCount: 100,
        isFollowing: false,
        createdAt: DateTime.utc(2024, 1, 1),
      );

      // Simulate follow
      final followedUser = user.copyWith(
        isFollowing: true,
        followersCount: user.followersCount + 1,
      );

      expect(followedUser.isFollowing, true);
      expect(followedUser.followersCount, 101);

      // Simulate unfollow
      final unfollowedUser = followedUser.copyWith(
        isFollowing: false,
        followersCount: followedUser.followersCount - 1,
      );

      expect(unfollowedUser.isFollowing, false);
      expect(unfollowedUser.followersCount, 100);
    });
  });
}

