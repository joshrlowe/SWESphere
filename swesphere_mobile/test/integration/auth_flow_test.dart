import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/auth/data/models/user_model.dart';
import 'package:swesphere_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:swesphere_mobile/features/auth/domain/usecases/login.dart';
import 'package:swesphere_mobile/features/auth/domain/usecases/register.dart';

void main() {
  group('Auth Flow Integration', () {
    test('User entity -> UserModel -> JSON -> UserModel -> User entity round-trip', () {
      // Create original entity
      final originalUser = User(
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        displayName: 'Test User',
        bio: 'This is my bio',
        avatarUrl: 'https://example.com/avatar.jpg',
        bannerUrl: 'https://example.com/banner.jpg',
        location: 'San Francisco, CA',
        website: 'https://testuser.com',
        followersCount: 1000,
        followingCount: 500,
        postsCount: 250,
        isVerified: true,
        isFollowing: false,
        createdAt: DateTime.utc(2024, 1, 1),
      );

      // Convert to model
      final model = UserModel.fromEntity(originalUser);

      // Convert to JSON
      final json = model.toJson();

      // Convert back to model
      final restoredModel = UserModel.fromJson(json);

      // Convert back to entity
      final restoredUser = restoredModel.toEntity();

      // Verify all fields match
      expect(restoredUser.id, originalUser.id);
      expect(restoredUser.username, originalUser.username);
      expect(restoredUser.email, originalUser.email);
      expect(restoredUser.displayName, originalUser.displayName);
      expect(restoredUser.bio, originalUser.bio);
      expect(restoredUser.avatarUrl, originalUser.avatarUrl);
      expect(restoredUser.bannerUrl, originalUser.bannerUrl);
      expect(restoredUser.location, originalUser.location);
      expect(restoredUser.website, originalUser.website);
      expect(restoredUser.followersCount, originalUser.followersCount);
      expect(restoredUser.followingCount, originalUser.followingCount);
      expect(restoredUser.postsCount, originalUser.postsCount);
      expect(restoredUser.isVerified, originalUser.isVerified);
      expect(restoredUser.isFollowing, originalUser.isFollowing);
    });

    test('LoginParams validation', () {
      const validParams = LoginParams(
        email: 'test@example.com',
        password: 'password123',
      );

      expect(validParams.email, isNotEmpty);
      expect(validParams.password, isNotEmpty);
    });

    test('RegisterParams complete validation', () {
      const params = RegisterParams(
        username: 'valid_user',
        email: 'valid@example.com',
        password: 'SecurePass123!',
      );

      expect(params.validateUsername(), isNull);
      expect(params.validateEmail(), isNull);
      expect(params.validatePassword(), isNull);
    });

    test('AuthTokens creation', () {
      const tokens = AuthTokens(
        accessToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        refreshToken: 'refresh_token_value',
      );

      expect(tokens.accessToken, isNotEmpty);
      expect(tokens.refreshToken, isNotEmpty);
    });
  });
}

