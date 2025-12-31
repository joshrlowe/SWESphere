import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/profile/domain/entities/profile.dart';

void main() {
  final testUser = User(
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    displayName: 'Test User',
    followersCount: 100,
    followingCount: 50,
    createdAt: DateTime(2024, 1, 1),
  );

  group('Profile', () {
    test('creates with required fields', () {
      final profile = Profile(user: testUser);

      expect(profile.user, testUser);
      expect(profile.isOwnProfile, false);
      expect(profile.isBlocked, false);
      expect(profile.isMuted, false);
    });

    test('creates with all fields', () {
      final profile = Profile(
        user: testUser,
        isOwnProfile: true,
        isBlocked: false,
        isMuted: true,
      );

      expect(profile.isOwnProfile, true);
      expect(profile.isMuted, true);
    });

    test('copyWith updates specified fields', () {
      final profile = Profile(user: testUser);
      final updated = profile.copyWith(
        isOwnProfile: true,
        isMuted: true,
      );

      expect(updated.isOwnProfile, true);
      expect(updated.isMuted, true);
      expect(updated.isBlocked, false);
      expect(updated.user, testUser);
    });

    test('equality works correctly', () {
      final profile1 = Profile(user: testUser);
      final profile2 = Profile(user: testUser);
      final profile3 = Profile(user: testUser, isOwnProfile: true);

      expect(profile1, equals(profile2));
      expect(profile1, isNot(equals(profile3)));
    });
  });

  group('ProfileStats', () {
    test('creates with defaults', () {
      const stats = ProfileStats();

      expect(stats.postsCount, 0);
      expect(stats.followersCount, 0);
      expect(stats.followingCount, 0);
      expect(stats.likesCount, 0);
    });

    test('creates with all fields', () {
      const stats = ProfileStats(
        postsCount: 100,
        followersCount: 500,
        followingCount: 200,
        likesCount: 1000,
      );

      expect(stats.postsCount, 100);
      expect(stats.followersCount, 500);
      expect(stats.followingCount, 200);
      expect(stats.likesCount, 1000);
    });

    test('equality works correctly', () {
      const stats1 = ProfileStats(postsCount: 10, followersCount: 20);
      const stats2 = ProfileStats(postsCount: 10, followersCount: 20);
      const stats3 = ProfileStats(postsCount: 10, followersCount: 30);

      expect(stats1, equals(stats2));
      expect(stats1, isNot(equals(stats3)));
    });
  });
}

