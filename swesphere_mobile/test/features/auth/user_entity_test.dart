import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';

void main() {
  group('User entity', () {
    final testUser = User(
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      displayName: 'Test User',
      bio: 'A test bio',
      avatarUrl: 'https://example.com/avatar.jpg',
      bannerUrl: 'https://example.com/banner.jpg',
      location: 'San Francisco',
      website: 'https://example.com',
      followersCount: 100,
      followingCount: 50,
      postsCount: 25,
      isVerified: true,
      isFollowing: false,
      createdAt: DateTime(2024, 1, 1),
    );

    test('creates user with all properties', () {
      expect(testUser.id, 1);
      expect(testUser.username, 'testuser');
      expect(testUser.email, 'test@example.com');
      expect(testUser.displayName, 'Test User');
      expect(testUser.bio, 'A test bio');
      expect(testUser.followersCount, 100);
      expect(testUser.followingCount, 50);
      expect(testUser.postsCount, 25);
      expect(testUser.isVerified, true);
      expect(testUser.isFollowing, false);
    });

    test('name returns displayName when available', () {
      expect(testUser.name, 'Test User');
    });

    test('name returns username when displayName is null', () {
      final userWithoutDisplayName = User(
        id: 2,
        username: 'noname',
        email: 'noname@example.com',
        createdAt: DateTime(2024, 1, 1),
      );
      expect(userWithoutDisplayName.name, 'noname');
    });

    test('handle returns username with @', () {
      expect(testUser.handle, '@testuser');
    });

    test('copyWith creates new user with updated fields', () {
      final updatedUser = testUser.copyWith(
        displayName: 'Updated Name',
        followersCount: 200,
      );

      expect(updatedUser.displayName, 'Updated Name');
      expect(updatedUser.followersCount, 200);
      // Other fields unchanged
      expect(updatedUser.username, 'testuser');
      expect(updatedUser.email, 'test@example.com');
    });

    test('copyWith preserves original when no changes', () {
      final copiedUser = testUser.copyWith();
      expect(copiedUser, equals(testUser));
    });

    test('equality works correctly', () {
      final user1 = User(
        id: 1,
        username: 'user1',
        email: 'user1@test.com',
        createdAt: DateTime(2024, 1, 1),
      );
      final user2 = User(
        id: 1,
        username: 'user1',
        email: 'user1@test.com',
        createdAt: DateTime(2024, 1, 1),
      );
      final user3 = User(
        id: 2,
        username: 'user2',
        email: 'user2@test.com',
        createdAt: DateTime(2024, 1, 1),
      );

      expect(user1, equals(user2));
      expect(user1, isNot(equals(user3)));
    });

    test('default values are set correctly', () {
      final minimalUser = User(
        id: 1,
        username: 'minimal',
        email: 'minimal@test.com',
        createdAt: DateTime(2024, 1, 1),
      );

      expect(minimalUser.followersCount, 0);
      expect(minimalUser.followingCount, 0);
      expect(minimalUser.postsCount, 0);
      expect(minimalUser.isVerified, false);
      expect(minimalUser.isFollowing, false);
      expect(minimalUser.displayName, isNull);
      expect(minimalUser.bio, isNull);
      expect(minimalUser.avatarUrl, isNull);
    });
  });
}

