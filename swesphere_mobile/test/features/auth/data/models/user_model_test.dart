import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/data/models/user_model.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';

void main() {
  group('UserModel', () {
    final testJson = {
      'id': 1,
      'username': 'testuser',
      'email': 'test@example.com',
      'display_name': 'Test User',
      'bio': 'A test bio',
      'avatar_url': 'https://example.com/avatar.jpg',
      'banner_url': 'https://example.com/banner.jpg',
      'location': 'San Francisco',
      'website': 'https://example.com',
      'followers_count': 100,
      'following_count': 50,
      'posts_count': 25,
      'is_verified': true,
      'is_following': false,
      'created_at': '2024-01-01T00:00:00.000Z',
    };

    final testUserModel = UserModel(
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
      createdAt: DateTime.utc(2024, 1, 1),
    );

    group('fromJson', () {
      test('creates UserModel from valid JSON', () {
        final model = UserModel.fromJson(testJson);

        expect(model.id, 1);
        expect(model.username, 'testuser');
        expect(model.email, 'test@example.com');
        expect(model.displayName, 'Test User');
        expect(model.bio, 'A test bio');
        expect(model.avatarUrl, 'https://example.com/avatar.jpg');
        expect(model.bannerUrl, 'https://example.com/banner.jpg');
        expect(model.location, 'San Francisco');
        expect(model.website, 'https://example.com');
        expect(model.followersCount, 100);
        expect(model.followingCount, 50);
        expect(model.postsCount, 25);
        expect(model.isVerified, true);
        expect(model.isFollowing, false);
      });

      test('handles minimal JSON with defaults', () {
        final minimalJson = {
          'id': 1,
          'username': 'minimal',
          'email': 'minimal@test.com',
          'created_at': '2024-01-01T00:00:00.000Z',
        };

        final model = UserModel.fromJson(minimalJson);

        expect(model.id, 1);
        expect(model.username, 'minimal');
        expect(model.displayName, isNull);
        expect(model.bio, isNull);
        expect(model.followersCount, 0);
        expect(model.followingCount, 0);
        expect(model.postsCount, 0);
        expect(model.isVerified, false);
        expect(model.isFollowing, false);
      });
    });

    group('toJson', () {
      test('converts UserModel to JSON', () {
        final json = testUserModel.toJson();

        expect(json['id'], 1);
        expect(json['username'], 'testuser');
        expect(json['email'], 'test@example.com');
        expect(json['display_name'], 'Test User');
        expect(json['bio'], 'A test bio');
        expect(json['avatar_url'], 'https://example.com/avatar.jpg');
        expect(json['followers_count'], 100);
        expect(json['following_count'], 50);
        expect(json['is_verified'], true);
        expect(json['is_following'], false);
      });
    });

    group('toEntity', () {
      test('converts UserModel to User entity', () {
        final entity = testUserModel.toEntity();

        expect(entity, isA<User>());
        expect(entity.id, 1);
        expect(entity.username, 'testuser');
        expect(entity.email, 'test@example.com');
        expect(entity.displayName, 'Test User');
        expect(entity.bio, 'A test bio');
        expect(entity.followersCount, 100);
        expect(entity.isVerified, true);
      });
    });

    group('fromEntity', () {
      test('creates UserModel from User entity', () {
        final user = User(
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          displayName: 'Test User',
          followersCount: 100,
          createdAt: DateTime.utc(2024, 1, 1),
        );

        final model = UserModel.fromEntity(user);

        expect(model.id, 1);
        expect(model.username, 'testuser');
        expect(model.displayName, 'Test User');
        expect(model.followersCount, 100);
      });
    });

    group('round-trip conversion', () {
      test('entity -> model -> entity preserves data', () {
        final originalEntity = User(
          id: 1,
          username: 'roundtrip',
          email: 'roundtrip@test.com',
          displayName: 'Round Trip User',
          bio: 'Testing round trip',
          followersCount: 50,
          followingCount: 25,
          isVerified: true,
          createdAt: DateTime.utc(2024, 1, 1),
        );

        final model = UserModel.fromEntity(originalEntity);
        final restoredEntity = model.toEntity();

        expect(restoredEntity.id, originalEntity.id);
        expect(restoredEntity.username, originalEntity.username);
        expect(restoredEntity.email, originalEntity.email);
        expect(restoredEntity.displayName, originalEntity.displayName);
        expect(restoredEntity.bio, originalEntity.bio);
        expect(restoredEntity.followersCount, originalEntity.followersCount);
        expect(restoredEntity.isVerified, originalEntity.isVerified);
      });
    });
  });
}

